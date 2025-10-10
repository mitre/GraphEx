// external modules
const { marked } = require('marked');
const path = require('path'); // filesystem operations
const fs = require('fs'); // filesystem operations

// constants
const DOCS_RELATIVE_PATH = '../docs/';
const INPUT_DIR_NAME = 'markdown';
const INPUT_FILEPATH = path.resolve(__dirname, DOCS_RELATIVE_PATH + INPUT_DIR_NAME);
const OUTPUT_DIR_NAME = 'html';
const OUTPUT_LOCATION = path.resolve(__dirname, DOCS_RELATIVE_PATH + OUTPUT_DIR_NAME);

/**
 * Traverse the file tree and find all files with the given extension.
 * This function can be recursive if nested directories are present.
 * @param {String} directoryPathToWalk the absolute path to the directory to walk
 * @param {String} fileExt the file extension to look for and save to the output dictionary
 * @returns {Dict.<String, String>} a dictionary containing filenames as the keys and file paths as the values
 */
function traverseDir(directoryPathToWalk) {
	// array of all paths to convert
	let pathsArray = [];
	try {
		// temp array of filenames in this directory path
		const files = fs.readdirSync(directoryPathToWalk);
		// for each file pointer in this directory
		files.forEach((filePtr) => {
			// create an absolute path to this file pointer
			const filePath = path.join(directoryPathToWalk, filePtr);
			pathsArray.push(filePath);
			if (fs.statSync(filePath).isDirectory() && filePtr != '.git') {
				// if this is a directory, we will have to use recursion to extract more files
				pathsArray.push(...traverseDir(filePath));
			}
		});
	} catch (e) {
		console.log('ERROR: failed to traverse directory:', directoryPathToWalk, ' ... error:', e);
		throw e;
	}
	return pathsArray;
}

/**
 * Adds tags to the HTML that markedJS doesn't account for
 * @param {String} currentHtml the HTML of the '.md' file parse by markedJS
 * @param {Number} level where this file is in relation to the index file (level 0)
 * @returns An HTML formatted more like you would expect one to be
 */
function insertHtmlSections(currentHtml, level) {
	let styleFilename = 'graphexStyle.css';
	for (let i = 0; i < level; i++) {
		styleFilename = '../' + styleFilename;
	}
	return (
		'<!DOCTYPE html>\n<html>\n<head>\n<link rel="stylesheet" href="' +
		styleFilename +
		'">\n</head>\n<body>\n\n' +
		currentHtml +
		'\n</body>\n</html>'
	);
}

/**
 * Converts an image path into a base64 string
 * @param {String} imagePath The path to the image to convert
 * @returns {String} the base64 encoded string prefixed with: 'data:image/png,base64,'
 */
function base64encodePng(imagePath) {
	return 'data:image/png;base64, ' + fs.readFileSync(imagePath, { encoding: 'base64' });
}

/**
 * Replaces the paths to images in the HTML with base64 encoded data (instead of the path)
 * @param {String} htmlString the HTML in which to search for images in
 * @param {String} filePath the path to the markdown file currently being converted
 * @returns The HTML string with all paths to images replaced
 */
function updateImgPaths(htmlString, filePath) {
	const replaceObj = {};
	const lines = htmlString.split(/\r?\n/);

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i];
		// find where the tag starts
		let indexLoc = line.indexOf('<img ');
		// loop through all anchor tags in this line (could be a p tag or something that has many anchors)
		while (indexLoc > -1) {
			const imgTag = line.slice(indexLoc, line.indexOf('>', indexLoc) + 1);
			const srcStartIndex = imgTag.indexOf('src=');
			const currentSrc = imgTag.slice(srcStartIndex + 5, imgTag.indexOf('"', srcStartIndex + 6));
			const newSrc = filePath.slice(0, filePath.lastIndexOf('/') + 1) + currentSrc;
			replaceObj[currentSrc] = base64encodePng(newSrc);
			// update our index pointer to find the next img tag
			indexLoc = line.indexOf('<img ', indexLoc + 1);
		}
	}

	const keys = Object.keys(replaceObj);

	if (keys.length) {
		keys.forEach((key) => {
			htmlString = htmlString.replace(key, replaceObj[key]);
		});
	}

	return htmlString;
}

/**
 * Custom renderer to override some of the functionality of markedjs
 */
class CustomRender extends marked.Renderer {
	paragraph(text) {
		const firstIndex = text.indexOf('$');
		if (firstIndex < 0) {
			return '<p>' + text + '</p>';
		}
		const lastIndex = text.indexOf('$', firstIndex + 1);
		const className = text.slice(firstIndex + 1, lastIndex);
		const words = text.slice(lastIndex + 1);
		return "<p><span class='" + className + "'>" + className.toUpperCase() + ': </span>' + words + '</p>';
	}
}

// convert the files
console.log('Converting markdown documentation files from path:', INPUT_FILEPATH);

// remove old HTML files
if (fs.existsSync(OUTPUT_LOCATION)) {
	fs.rmSync(OUTPUT_LOCATION, { recursive: true, force: true });
}
fs.mkdirSync(OUTPUT_LOCATION);

const allPathsArray = traverseDir(INPUT_FILEPATH);

if (allPathsArray.length <= 0) {
	throw 'No markdown documentation files found!';
}

allPathsArray.forEach((filepath) => {
	if (fs.statSync(filepath).isFile()) {
		if (filepath.endsWith('.md')) {
			let html = marked.parse(fs.readFileSync(filepath).toString().replaceAll(".md", ".html"), {
				renderer: new CustomRender(),
				pedantic: false,
				gfm: true,
				breaks: true,
				sanitize: true,
				silent: true,
				smartLists: true,
				smartypants: false,
				mangle: false, // prevents marked from creating different combinations of characters in email addresses each run
				xhtml: false
			});

			// replace paths to images with base64 strings
			html = updateImgPaths(html, filepath);

			const newFilePath = filepath
				.replace(INPUT_DIR_NAME, function () {
					return OUTPUT_DIR_NAME;
				})
				.replace('.md', function () {
					return '.html';
				});

			const level = newFilePath.split('/docs/html/')[1].split('/').length - 1;

			// replaces file by default
			fs.writeFileSync(newFilePath, insertHtmlSections(html, level));
		} else if (!filepath.includes('images')) {
			fs.copyFileSync(
				filepath,
				filepath.replace(INPUT_DIR_NAME, function () {
					return OUTPUT_DIR_NAME;
				})
			);
		}
	} else {
		// is directory
		const dirPath = filepath.replace(INPUT_DIR_NAME, function () {
			return OUTPUT_DIR_NAME;
		});
		if (!fs.existsSync(dirPath) && !dirPath.includes('images')) {
			fs.mkdirSync(dirPath, { recursive: true });
		}
	}
});

console.log('Finished converting documentation to HTML.');
