import { Graph } from '@/graph';
import { useMetadataStore, usePromptStore } from '@/stores';
import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import { computed, reactive } from 'vue';

interface FileInitData {
	name: string;
	isDir: boolean;
	children: Array<FileInitData>;
}

export const GRAPH_FILE_EXTENSION = '.gx';
export const LOG_FILE_EXTENSION = '.log';

/**
 * Object representing a file on disk.
 */
export interface FileObject {
	/** Unique ID for this particular file object. This ID will be maintained between refreshes for the same file (for as long as the file is not deleted). */
	id: string;

	/** The parent directory of this file, or `null` if there is no parent. The path to this file is derived by taking the names of all parents until `null` is reached. */
	parent: FileObject | null;

	/** The name of this file (including extension). */
	name: string;

	/** Whether this is a directory. */
	isDir: boolean;

	/** Child files (if this is a directory). */
	children: Array<FileObject>;
}

export const useFileStore = defineStore('files', () => {
	const promptStore = usePromptStore();

	/** Descriptions of the currently active file operations (used to show a loading screen). */
	const activeFileOperations = reactive<Array<string>>([]);

	/**
	 * The tracked file system. All files tracked here are known to exist on persistent storage.
	 *
	 * Files (and children arrays of files) are always sorted such that directories come first and then lexicographically. This is enforced only by the
	 * backend and any manual updates to this file tree needs to preserve this ordering.
	 */
	const files = reactive<Array<FileObject>>([]);

	/** Mapping of file ID to the file. */
	const fileIdMap = computed(() => {
		const idMap: { [id: string]: FileObject } = {};
		const walkAndAddToMap = (fileList: Array<FileObject>) => {
			for (const file of fileList) {
				idMap[file.id] = file;
				walkAndAddToMap(file.children);
			}
		};
		walkAndAddToMap(files);
		return idMap;
	});

	/**
	 * Fetch file data from the backend and update the tracked file data.
	 *
	 * @param ids A dictionary mapping file path to a custom ID. This should be used when a known file should be assigned a specific ID. Note that
	 * unless this file does not exist in the file tree already, this is not needed as files will automatically maintain their IDs due to the fact that
	 * IDs are maintained for the same file path between updates. Setting an ID value to `null` will always regenerate the ID for that path.
	 */
	async function refreshFiles(ids?: { [path: string]: string | null }) {
		ids = ids || {};
		activeFileOperations.push('Refreshing Files');
		try {
			// Fetch the file data from the server
			const response = await fetch('/api/files', { method: 'GET' });
			if (!response.ok) {
				const message = await response.text();
				promptStore.failedAlert('Failed To Fetch Files', `Server returned status ${response.status}: ${message}`);
				return;
			}

			const data: Array<FileInitData> = await response.json();
			if (!Array.isArray(data)) {
				promptStore.failedAlert('Failed To Fetch Files', `Returned data is not an array.`);
				return;
			}

			// Populate an object that maps paths to IDs on the new file tree.
			// Any path not found in this object will have a new ID generated for it.
			// We'll first copy over all the IDs already in the tree (to maintain IDs between updates),
			// and then take any IDs specified as a parameter.
			const idsToSet: { [path: string]: string | null } = {};
			const filesToIterate: Array<FileObject> = [...files];
			while (filesToIterate.length) {
				const file = filesToIterate.shift()!;
				const path = getFilePath(file);
				if (path.length > 0) {
					idsToSet[path] = file.id;
				}
				filesToIterate.push(...file.children);
			}

			for (const path of Object.keys(ids)) {
				idsToSet[normalizePath(path)] = ids[path] ? ids[path] : null;
			}

			// Define a recursive function that will walk the init data from the server
			// and create the tree
			const fileInitDataToFile = (
				parent: FileObject | null,
				initData: FileInitData,
				currentPathComponents: Array<string>
			): FileObject => {
				const newPathComponents = [...currentPathComponents, initData.name];
				const currentPath = newPathComponents.join('/');
				const id = currentPath in idsToSet ? idsToSet[currentPath] || uuidv4() : uuidv4();
				const data: FileObject = {
					parent: parent,
					id: id,
					name: initData.name,
					isDir: initData.isDir,
					children: []
				};
				data.children = initData.children.map((child) => fileInitDataToFile(data, child, newPathComponents));
				return data;
			};

			// Replace the old file tree with the new file tree.
			files.splice(0, files.length, ...data.map((d) => fileInitDataToFile(null, d, [])));

			// Display a warning if too many files were loaded
			const countFiles = (filesRef: Array<FileObject>): number => {
				let count = filesRef.length;
				for (const file of filesRef) {
					count += countFiles(file.children);
				}
				return count;
			};

			const fileCount = countFiles(files);
			if (fileCount >= 2500) {
				promptStore.failedAlert(
					'Too Many Files.',
					`The root directory loaded has ${fileCount} files. Consider choosing a directory containing fewer files to improve performance.`
				);
			}
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Find a file by its ID in the `files` tree.
	 *
	 * @param fileId The ID to search for.
	 *
	 * @returns The file data, or `null` if the file was not found.
	 */
	function findFileById(id: string): FileObject | null {
		return id in fileIdMap.value ? fileIdMap.value[id] : null;
	}

	/**
	 * Find a file by its path in the `files` tree.
	 *
	 * @param path The path to search for.
	 *
	 * @returns The file data, or `null` if the file was not found.
	 */
	function findFileByPath(path: string): FileObject | null {
		const pathComponents = normalizePath(path).trim().split('/');
		let candidateFiles: Array<FileObject> = files;
		while (pathComponents.length) {
			const index = candidateFiles.findIndex((f) => f.name === pathComponents[0]);
			if (index === -1) {
				return null;
			}

			if (pathComponents.length === 1) {
				return candidateFiles[index];
			}

			candidateFiles = candidateFiles[index].children;
			pathComponents.shift();
		}

		return null;
	}

	/**
	 * Get the name of a file.
	 *
	 * @param file The file object, or the file ID.
	 * @param removeExt If `true`, do not include the extension of the file in the name (default `false`).
	 *
	 * @returns The name of the file. This will be an empty string if an ID is provided but a file does not exist for that ID.
	 */
	function getFileName(fileOrId: FileObject | string, removeExt: boolean = false): string {
		const file = typeof fileOrId === 'string' ? findFileById(fileOrId) : fileOrId;
		if (!file) {
			return '';
		}

		let name = file.name;
		if (removeExt) {
			const lastDotIndex = name.lastIndexOf('.');
			if (lastDotIndex !== -1) {
				name = name.slice(0, lastDotIndex);
			}
		}
		return name;
	}

	/**
	 * Get the full path of a file.
	 *
	 * @param file The file object, or the file ID.
	 *
	 * @returns The path to the file. This will be an empty string if an ID is provided but a file does not exist for that ID.
	 */
	function getFilePath(fileOrId: FileObject | string): string {
		const file = typeof fileOrId === 'string' ? findFileById(fileOrId) : fileOrId;
		if (!file) {
			return '';
		}

		const pathComponents: Array<string> = [];
		let currentFile: FileObject | null = file;
		while (currentFile) {
			pathComponents.unshift(currentFile.name);
			currentFile = 'parent' in currentFile ? currentFile.parent : null;
		}
		return pathComponents.join('/');
	}

	/**
	 * Normalize a path string (remove leading `./`, `../`, etc, and trailing `/`). Normalized paths will follow the same
	 * format as returned by the `getFilePath` function and may be used for direct comparisons.
	 *
	 * @param path The path to format.
	 *
	 * @returns The formatted path.
	 */
	function normalizePath(path: string): string {
		let p = path.replace(/\\/gm, '/');
		p = p.replace(/^(\.+\/|\/?)+/gm, '');
		p = p.replace(/\/+$/gm, '');
		return p;
	}

	/**
	 * Opens a modal popup window for creating a new file.
	 *
	 * @param baseName The value to pre-populate the input field.
	 *
	 * @returns The ID for the newly created file, or null if this failed.
	 */
	async function promptCreateFile(baseName: string = ''): Promise<string | null> {
		const value = await promptStore.show({
			title: 'Create New Graph File',
			entries: [
				{
					label: 'File Path',
					help: 'The path to the file to create (will error if this name already exists).',
					field: {
						value: baseName
					},
					focus: true
				},
				{
					label: 'Graph File',
					help: `Whether this is a graph file. If checked, this file will be created as an empty graph and the '${GRAPH_FILE_EXTENSION}' extension will be added to the file name (if not already provided).`,
					togglable: true,
					isToggled: true
				}
			],
			buttons: [
				{
					text: 'Create File',
					type: 'primary'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			]
		});

		if (!value || value.buttonName == 'Cancel') {
			return null;
		}

		let path = normalizePath(value.form.entries[0].field!.value);
		const isGraphIsChecked = value?.form.entries[1].isToggled;
		activeFileOperations.push(`Creating ${path}`);
		try {
			let contents = '';
			if (isGraphIsChecked || path.toLowerCase().endsWith('.gx')) {
				path = path.toLowerCase().endsWith(GRAPH_FILE_EXTENSION) ? path : path + GRAPH_FILE_EXTENSION;
				const g = new Graph();

				// Add the default nodes
				const metadataStore = useMetadataStore();
				const start = g.addNode(metadataStore.getNode('Graph Start'), 200, 200);
				const print = g.addNode(metadataStore.getNode('Log (Print)'), 407, 200);
				const end = g.addNode(metadataStore.getNode('End'), 740, 200);

				// Set the initial print value
				print.inputSockets[0].fieldValue = 'Hello World!';

				// Connect the nodes together
				print.getInputSocket('_backward').connect(start.getOutputSocket('_forward'));
				print.getOutputSocket('_forward').connect(end.getInputSocket('_backward'));

				// get the serialized graph to save to disk
				contents = g.getSerializedGraphString();
			}

			return await writeToDisk(path, contents, false);
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Opens the modal popup window for 'Create Directory'
	 *
	 * @param baseDirectory The value to pre-populate the input field.
	 *
	 * @returns The newly created directory, or null if this failed.
	 */
	async function promptCreateDirectory(baseDirectory: string = ''): Promise<FileObject | null> {
		const value = await promptStore.show({
			title: 'Create New Directory',
			entries: [
				{
					label: 'Directory Path',
					help: 'The path to the directory to create (will error if this path already exists). All intermediate directories will be created.',
					field: {
						value: baseDirectory
					},
					focus: true
				}
			],
			buttons: [
				{
					text: 'Create Directory',
					type: 'primary'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			]
		});

		if (!value || value.buttonName == 'Cancel') {
			return null;
		}

		const path = normalizePath(value.form.entries[0].field!.value);
		activeFileOperations.push('Creating New Directory');
		try {
			const response = await fetch('/api/directory?path=' + path, { method: 'POST' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			await refreshFiles();
			const file = findFileByPath(path);
			if (!file) {
				await promptStore.failedAlert('Failed to Find Directory', `Unable to find directory '${path}' after creation.`);
				return null;
			}

			return file;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed to Create Directory',
				`Failed to create directory: ${path} (${e instanceof Error ? e.toString() : String(e)})`
			);
			return null;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Get the text contents of a file as a string.
	 *
	 * @param fileIdOrFile The file ID.
	 * @param base64 When set to true: will use a different endpoint on the server to base64 encode the file contents when returning them
	 *
	 * @returns The file contents as a string, or `null` if the file contents could not be fetched.
	 */
	async function getFileContents(id: string, base64?: boolean): Promise<string | null> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Failed To Get File', 'File does not exist on disk.');
			return null;
		}

		const filePath = getFilePath(file);
		activeFileOperations.push('Getting File Contents');
		try {
			let apiPath = '/api/file?path=';
			if (base64) apiPath = '/api/baseSixtyFourFile?path=';
			const response = await fetch(apiPath + filePath, { method: 'GET' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}
			return await response.text();
		} catch (e) {
			await promptStore.failedAlert(
				'Failed To Get File',
				`Failed to get file contents from path "${filePath}". (${e instanceof Error ? e.toString() : String(e)})`
			);
			return null;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Write the contents of a file to disk. If the file does not exist, it will be created.
	 *
	 * This function will automatically refresh the file tree after writing the file.
	 *
	 * @param filepath The path to write to.
	 * @param contents The contents of the file to write as a string.
	 * @param overwrite Whether to allow overwriting of existing files.
	 *
	 * @returns The ID of the file that was written to, or `null` if the write failed.
	 */
	async function writeToDisk(filepath: string, contents: string, overwrite: boolean): Promise<string | null> {
		filepath = normalizePath(filepath);
		activeFileOperations.push(`Writing ${filepath}`);
		try {
			const response = await fetch('/api/file?path=' + filepath + '&overwrite=' + overwrite, {
				method: 'POST',
				body: contents
			});

			if (!response.ok && response.status === 409) {
				await promptStore.failedAlert('Failed To Save File', `File '${filepath}' already exists.`);
				await refreshFiles();
				return null;
			}

			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			await refreshFiles();
			const file = findFileByPath(filepath);
			if (!file) {
				await promptStore.failedAlert('Failed to Find File', `Unable to find file '${filepath}' after write.`);
				return null;
			}
			return file.id;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed To Save File',
				`Failed to save file to path "${filepath}". (${e instanceof Error ? e.toString() : String(e)})`
			);
			return null;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Opens a modal popup window for renaming this file.
	 *
	 * The file will maintain its ID after the rename.
	 *
	 * @param id The file ID for the file to rename.
	 *
	 * @returns A boolean whether the rename succeeded.
	 */
	async function promptRename(id: string): Promise<boolean> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Unable To Rename File', 'File does not exist on disk.');
			return false;
		}

		const filePath = getFilePath(file);
		const value = await promptStore.show({
			title: `Rename ${filePath}`,
			entries: [
				{
					label: 'New Name',
					help: 'The desired name of the file or directory (will error if this name already exists).',
					field: {
						value: getFileName(file)
					},
					focus: true
				}
			],
			buttons: [
				{
					text: 'Rename',
					type: 'primary'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			]
		});

		if (!value || value.buttonName == 'Cancel') {
			return false;
		}

		let newName = value.form.entries[0].field!.value;

		// add the gx extension if one is missing now
		if (filePath.toLowerCase().endsWith('.gx') && !newName.toLowerCase().endsWith('.gx')) {
			newName += '.gx';
		}

		return await renameFile(id, newName);
	}

	/**
	 * Rename a file. This will only change the file name while keeping the directory path components (if any) the same.
	 *
	 * The file will maintain its ID after the rename.
	 *
	 * @param id The file ID for the file to rename.
	 * @param newName The new name for the file.
	 *
	 * @returns A boolean whether the rename succeeded.
	 */
	async function renameFile(id: string, newName: string): Promise<boolean> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Failed To Rename File', 'File does not exist on disk.');
			return false;
		}

		const newNameTrimmed = newName.trim();
		if (newNameTrimmed.length === 0) {
			await promptStore.failedAlert('Failed To Rename File', 'Name cannot be empty.');
			return false;
		}

		if (newNameTrimmed === file.name) {
			// Nothing to do
			return true;
		}

		const dir = file.parent ? getFilePath(file.parent) : '';
		return await moveFile(id, dir + '/' + newNameTrimmed);
	}

	/**
	 * Move a file (change the file path).
	 *
	 * The file will maintain its ID after the move.
	 *
	 * @param id The file ID for the file to move.
	 * @param newPath The new path for the file.
	 *
	 * @returns A boolean whether the rename succeeded.
	 */
	async function moveFile(id: string, newPath: string): Promise<boolean> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Failed To Move File', 'File does not exist on disk.');
			return false;
		}

		const oldPath = getFilePath(file);
		newPath = normalizePath(newPath);
		activeFileOperations.push('Moving Path');
		try {
			const response = await fetch('/api/movePath?path=' + oldPath, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					newPath: newPath
				})
			});

			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			// Refresh the files to load the moved file, and provide the new path with the old ID to maintain references
			const idMap: { [path: string]: string | null } = {};
			idMap[newPath] = id;
			idMap[oldPath] = null;
			await refreshFiles(idMap);
			return true;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed to Move Path',
				`Failed to move path ${oldPath} to ${newPath} (${e instanceof Error ? e.toString() : String(e)})`
			);
			return false;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Duplicate a file. This will make a network request to duplicate the file on the underlying system.
	 *
	 * @param id The file ID for the file to duplicate.
	 *
	 * @returns The ID for the new file, or `null` if the duplication failed.
	 */
	async function duplicateFile(id: string): Promise<string | null> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Failed To Duplicate File', 'File does not exist on disk.');
			return null;
		}

		const filePath = getFilePath(file);
		activeFileOperations.push('Duplicating File');
		try {
			const response = await fetch('/api/duplicateFile?path=' + filePath, { method: 'GET' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			await refreshFiles();
			const duplicateFilePath = await response.text();
			const newFile = findFileByPath(duplicateFilePath);
			if (!newFile) {
				await promptStore.failedAlert(
					'Failed to Find File',
					`Unable to find file '${duplicateFilePath}' after creation.`
				);
				return null;
			}
			return newFile.id;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed to Duplicate File',
				`Failed to duplicate file ${filePath} (${e instanceof Error ? e.toString() : String(e)})`
			);
			return null;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Delete a file. Directories will be deleted recursively.
	 *
	 * @param id The file ID for the file to delete.
	 *
	 * @returns A boolean whether the operation was successful.
	 */
	async function deleteFile(id: string): Promise<boolean> {
		const file = findFileById(id);
		if (!file) {
			await promptStore.failedAlert('Failed To Move File', 'File does not exist on disk.');
			return false;
		}

		const filePath = getFilePath(file);
		activeFileOperations.push('Deleting Path');
		try {
			const response = await fetch('/api/file?path=' + filePath, { method: 'DELETE' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			await refreshFiles();
			return true;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed to Delete Path',
				`Failed to delete path ${filePath} (${e instanceof Error ? e.toString() : String(e)})`
			);
			return false;
		} finally {
			activeFileOperations.pop();
		}
	}

	/**
	 * Get the files in the file store as a string.
	 *
	 * @returns A string.
	 */
	function toString(): string {
		const filesToString = (children: Array<FileObject>, depth: number): string => {
			let s = '';
			for (const f of children) {
				s += ' -> '.repeat(depth) + `${getFilePath(f)} (ID=${f.id})\n`;
				s += filesToString(f.children, depth + 1);
			}
			return s;
		};

		return filesToString(files, 0);
	}

	/**
	 * Removes the root path values from a filepath if it exists.
	 * @returns a string of the formatted filepath. If an error occurs, it will return the original filepath.
	 */
	async function formatGitFilepath(filepath: string) {
		try {
			const response = await fetch('/api/git/formatGitFilepath?path=' + filepath, { method: 'GET' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}

			const formattedFilePath = await response.text();
			if (!formattedFilePath) {
				await promptStore.failedAlert('Error getting file path');
				return filepath;
			}
			return formattedFilePath;
		} catch (e) {
			await promptStore.failedAlert(
				'Failed to Format File',
				`Failed to format file ${filepath} (${e instanceof Error ? e.toString() : String(e)})`
			);
			return filepath;
		}
	}

	return {
		activeFileOperations,
		files,
		fileIdMap,
		refreshFiles,
		findFileById,
		findFileByPath,
		normalizePath,
		getFilePath,
		getFileName,
		promptCreateFile,
		promptCreateDirectory,
		getFileContents,
		writeToDisk,
		promptRename,
		renameFile,
		moveFile,
		duplicateFile,
		deleteFile,
		toString,
		formatGitFilepath
	};
});
