/**
 * FastUI x-flow Directive
 * Alpine.js directive for Flowbite component initialization
 */

import type { FlowbiteComponentType } from '../types';
import { debugLog, hasFlowbite, debounce } from '../utils/helpers';

/**
 * Flowbite component instances
 */
const flowbiteInstances = new Map<string, unknown>();

/**
 * Flowbite component initialization map
 * Maps component types to their initialization functions
 */
const componentInitializers: Record<string, (el: HTMLElement) => unknown> = {
  accordion: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Accordion) {
      const Accordion = (window as unknown as Record<string, { init?: (el: HTMLElement) => unknown }>).Accordion;
      return Accordion.init?.(el);
    }
    return null;
  },

  carousel: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Carousel) {
      const Carousel = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Carousel;
      return Carousel.init?.(el);
    }
    return null;
  },

  collapse: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Collapse) {
      const Collapse = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Collapse;
      return Collapse.init?.(el);
    }
    return null;
  },

  dropdown: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Dropdown) {
      const Dropdown = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Dropdown;
      return Dropdown.init?.(el);
    }
    return null;
  },

  modal: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Modal) {
      const Modal = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Modal;
      return Modal.init?.(el);
    }
    return null;
  },

  tabs: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Tabs) {
      const Tabs = (window as unknown as Record<string, { init?: (el: HTMLElement) => unknown }>).Tabs;
      return Tabs.init?.(el);
    }
    return null;
  },

  tooltip: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Tooltip) {
      const Tooltip = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Tooltip;
      return Tooltip.init?.(el);
    }
    return null;
  },

  popover: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Popover) {
      const Popover = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Popover;
      return Popover.init?.(el);
    }
    return null;
  },

  drawer: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Drawer) {
      const Drawer = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Drawer;
      return Drawer.init?.(el);
    }
    return null;
  },

  dismiss: (el) => {
    if (hasFlowbite() && (window as unknown as Record<string, unknown>).Dismiss) {
      const Dismiss = (window as unknown as Record<string, { init?: (el: HTMLElement, options?: unknown) => unknown }>).Dismiss;
      return Dismiss.init?.(el);
    }
    return null;
  },
};

/**
 * Create x-flow Alpine directive
 */
export function createFlowDirective() {
  return {
    name: 'flow',

    callback(el: HTMLElement, value: string): void {
      // Parse component type(s)
      const components = value.split(',').map((c) => c.trim()) as FlowbiteComponentType[];

      const initComponent = (type: FlowbiteComponentType) => {
        const initializer = componentInitializers[type];
        if (initializer) {
          try {
            const instance = initializer(el);
            if (instance) {
              const instanceId = `${type}-${Date.now()}`;
              flowbiteInstances.set(instanceId, instance);
              el.dataset[`flow${type.charAt(0).toUpperCase() + type.slice(1)}Id`] = instanceId;
              debugLog(`Flowbite ${type} initialized`, el);
            }
          } catch (e) {
            console.warn(`[FastUI] Failed to initialize ${type}:`, e);
          }
        } else {
          debugLog(`Unknown Flowbite component: ${type}`);
        }
      };

      // Initialize each component
      components.forEach(initComponent);
    },
  };
}

/**
 * Initialize all Flowbite components in an element
 */
export function initFlowbiteComponents(el: HTMLElement): void {
  // Find all elements with data-flowbite or x-flow attribute
  const elements = el.querySelectorAll('[x-flow], [data-flowbite]');

  elements.forEach((element) => {
    const htmlEl = element as HTMLElement;
    const types = htmlEl.getAttribute('x-flow') || htmlEl.dataset.flowbite || '';

    types.split(',').forEach((type) => {
      const trimmedType = type.trim() as FlowbiteComponentType;
      const initializer = componentInitializers[trimmedType];
      if (initializer) {
        try {
          initializer(htmlEl);
        } catch (e) {
          debugLog(`Failed to reinitialize ${trimmedType}`, e);
        }
      }
    });
  });

  // Also check the element itself
  const selfTypes = el.getAttribute('x-flow') || el.dataset?.flowbite;
  if (selfTypes) {
    selfTypes.split(',').forEach((type) => {
      const trimmedType = type.trim() as FlowbiteComponentType;
      const initializer = componentInitializers[trimmedType];
      if (initializer) {
        try {
          initializer(el);
        } catch (e) {
          debugLog(`Failed to reinitialize ${trimmedType}`, e);
        }
      }
    });
  }
}

/**
 * Cleanup Flowbite instances in an element
 */
export function cleanupFlowbiteComponents(el: HTMLElement): void {
  // Find and dispose all instances
  for (const [instanceId, instance] of flowbiteInstances.entries()) {
    // Check if instance DOM element is still in document
    if (instance && typeof (instance as { dispose?: () => void }).dispose === 'function') {
      try {
        (instance as { dispose: () => void }).dispose();
        flowbiteInstances.delete(instanceId);
      } catch {
        // Instance may already be disposed
      }
    }
  }
}

/**
 * Register custom Flowbite component initializer
 */
export function registerFlowbiteComponent(
  type: string,
  initializer: (el: HTMLElement) => unknown
): void {
  componentInitializers[type] = initializer;
  debugLog(`Registered Flowbite component: ${type}`);
}
