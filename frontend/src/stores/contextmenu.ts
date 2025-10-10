import type ContextMenu from '@/components/ContextMenu.vue';
import { defineStore } from 'pinia';
import { reactive } from 'vue';

type ContextMenuType = InstanceType<typeof ContextMenu>;

export const useContextmenuStore = defineStore('contextmenu', () => {
	const menus = reactive<{ [id: string]: ContextMenuType }>({});

	function setContextMenu(id: string, component?: any) {
		if (!component) {
			removeContextMenu(id);
		} else {
			menus[id] = component;
		}
	}

	function removeContextMenu(id: string) {
		delete menus[id];
	}

	function getContextMenu(id: string): ContextMenuType {
		if (id in menus) {
			return menus[id] as ContextMenuType;
		}

		throw `Context menu ${id} not found`;
	}

	/**
	 * Listen for a context menu event on an element and use the default context menu.
	 *
	 * This is needed rather than simply not specifying anything at all because the default context menu is
	 * disabled by default across the UI.
	 *
	 * @param element The element to listen to context menu events on.
	 * @param capture Listen to context menu events using this 'capture' value.
	 */
	function useDefault(element: HTMLElement, capture?: boolean) {
		const callback = (event: MouseEvent) => {
			event.stopPropagation();
			return;
		};

		element.addEventListener('contextmenu', callback, { capture: capture });
	}

	return {
		menus,
		setContextMenu,
		removeContextMenu,
		getContextMenu,
		useDefault
	};
});
