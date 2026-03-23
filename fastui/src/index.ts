/**
 * FastUI - Server-Driven Interactivity for FastStack
 * 
 * A high-performance, single-file CDN library that replaces React/Next.js runtime
 * with a Server-Driven Interactivity (SDI) stack.
 * 
 * @version 0.1.0
 * @author Omerhrr
 * @license MIT
 */

import type { FastUIAPI, FastUIConfig, FastUIPlugin, AlpineDirective, EChartsOption, EChartsInstance } from './types';
import { mergeConfig, isBrowser, hasAlpine, debugLog, loadScript } from './utils/helpers';
import { createFragmentCache, setupCacheMiddleware } from './utils/cache';
import { createStore, initAlpineStore, persistStore } from './utils/store';
import { createChartDirective, updateChart, getChartInstance, disposeChart, resizeAllCharts } from './directives/chart';
import { createFlowDirective, initFlowbiteComponents, cleanupFlowbiteComponents } from './directives/flow';
import { createLazyDirective, createInitFragmentDirective, cleanupLazyObservers } from './directives/lazy';
import { createHTMXPlugin, configureHTMXDefaults } from './plugins/htmx';
import {
  loadTailwind,
  loadFlowbite,
  loadECharts,
  loadAlpine,
  loadHTMX,
  loadAllDependencies,
  injectCSS,
  FASTUI_DEFAULT_STYLES,
} from './styles/tailwind';

// Version from package.json (injected by Vite)
declare const __VERSION__: string;
declare const __DEV__: boolean;

/**
 * FastUI Instance
 */
let fastUIInstance: FastUIAPI | null = null;

/**
 * Create FastUI instance
 */
function createFastUI(userConfig?: Partial<FastUIConfig>): FastUIAPI {
  const config = mergeConfig(userConfig);

  // Create store and cache
  const store = createStore();
  const cache = createFragmentCache(config.cacheTTL);

  // Plugin and directive registries
  const plugins = new Map<string, FastUIPlugin>();
  const directives = new Map<string, AlpineDirective>();

  // Track initialization state
  let initialized = false;

  /**
   * Initialize FastUI
   */
  async function init(): Promise<void> {
    if (initialized) {
      debugLog('FastUI already initialized');
      return;
    }

    debugLog('Initializing FastUI...');

    // Inject default styles
    injectCSS(FASTUI_DEFAULT_STYLES, 'fastui-default-styles');

    // Load dependencies if not present
    if (config.autoReinit !== false) {
      await loadAllDependencies();
    }

    // Initialize Alpine store integration
    initAlpineStore();

    // Register core directives with Alpine
    if (hasAlpine()) {
      registerAlpineDirectives();
    }

    // Install HTMX plugin
    if (config.autoReinit !== false) {
      const htmxPlugin = createHTMXPlugin();
      htmxPlugin.install(fastUIInstance!);
      plugins.set('htmx', htmxPlugin);

      configureHTMXDefaults();
    }

    // Setup cache middleware
    if (config.cacheEnabled) {
      setupCacheMiddleware(cache);
    }

    initialized = true;
    debugLog('FastUI initialized');

    // Dispatch ready event
    window.dispatchEvent(new CustomEvent('fastui:ready', { detail: { version: __VERSION__ } }));
  }

  /**
   * Register Alpine directives
   */
  function registerAlpineDirectives(): void {
    if (!hasAlpine()) return;

    // Register x-chart
    const chartDirective = createChartDirective();
    window.Alpine.directive(chartDirective.name, chartDirective.callback);
    directives.set(chartDirective.name, chartDirective);

    // Register x-flow
    const flowDirective = createFlowDirective();
    window.Alpine.directive(flowDirective.name, flowDirective.callback);
    directives.set(flowDirective.name, flowDirective);

    // Register x-lazy
    const lazyDirective = createLazyDirective();
    window.Alpine.directive(lazyDirective.name, lazyDirective.callback);
    directives.set(lazyDirective.name, lazyDirective);

    // Register x-init-fragment
    const initFragmentDirective = createInitFragmentDirective();
    window.Alpine.directive(initFragmentDirective.name, initFragmentDirective.callback);
    directives.set(initFragmentDirective.name, initFragmentDirective);

    debugLog('Alpine directives registered');
  }

  /**
   * Register a custom plugin
   */
  function registerPlugin(name: string, plugin: FastUIPlugin): void {
    if (plugins.has(name)) {
      console.warn(`[FastUI] Plugin "${name}" already registered`);
      return;
    }

    plugin.install(fastUIInstance!);
    plugins.set(name, plugin);
    debugLog(`Plugin registered: ${name}`);
  }

  /**
   * Register a custom directive
   */
  function registerDirective(name: string, directive: AlpineDirective): void {
    if (directives.has(name)) {
      console.warn(`[FastUI] Directive "${name}" already registered`);
      return;
    }

    if (hasAlpine()) {
      window.Alpine.directive(name, directive.callback);
    }

    directives.set(name, directive);
    debugLog(`Directive registered: ${name}`);
  }

  /**
   * Reinitialize components in an element
   */
  function reinit(el: HTMLElement): void {
    debugLog('Reinitializing element', el);

    // Reinitialize Alpine
    if (hasAlpine()) {
      const alpineElements = el.querySelectorAll('[x-data]');
      alpineElements.forEach((element) => {
        const htmlEl = element as HTMLElement;
        if (!(htmlEl as unknown as { __x?: unknown }).__x) {
          window.Alpine.initTree(htmlEl);
        }
      });
    }

    // Reinitialize Flowbite
    initFlowbiteComponents(el);

    // Resize charts
    resizeAllCharts();
  }

  /**
   * Lazy load a module
   */
  async function lazyLoad(module: string): Promise<void> {
    switch (module) {
      case 'echarts':
        await loadECharts();
        break;
      case 'flowbite':
        await loadFlowbite();
        break;
      case 'tailwind':
        await loadTailwind();
        break;
      case 'alpine':
        await loadAlpine();
        break;
      case 'htmx':
        await loadHTMX();
        break;
      default:
        console.warn(`[FastUI] Unknown module: ${module}`);
    }
  }

  /**
   * Create ECharts instance
   */
  async function createChart(el: HTMLElement, options: EChartsOption): Promise<EChartsInstance> {
    await loadECharts();

    if (typeof window.echarts === 'undefined') {
      throw new Error('[FastUI] ECharts not loaded');
    }

    const instance = window.echarts.init(el);
    instance.setOption(options);

    return instance;
  }

  /**
   * Initialize Flowbite component
   */
  function initFlowbite(el: HTMLElement, type: string): void {
    initFlowbiteComponents(el);
  }

  // Create the API object
  fastUIInstance = {
    version: __VERSION__,
    debug: config.debug || false,

    store,
    cache,
    plugins,
    directives,

    init,
    registerPlugin,
    registerDirective,
    reinit,
    lazyLoad,
    createChart,
    initFlowbite,
  };

  return fastUIInstance;
}

// Auto-initialize when DOM is ready
if (isBrowser()) {
  // Create global instance
  window.FastUI = createFastUI();

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.FastUI.init();
    });
  } else {
    // DOM already loaded
    window.FastUI.init();
  }
}

// Export for module usage
export {
  createFastUI,
  createChartDirective,
  createFlowDirective,
  createLazyDirective,
  createHTMXPlugin,
  createFragmentCache,
  createStore,
  loadTailwind,
  loadFlowbite,
  loadECharts,
  loadAlpine,
  loadHTMX,
  loadAllDependencies,
  updateChart,
  getChartInstance,
  disposeChart,
  resizeAllCharts,
  initFlowbiteComponents,
  cleanupFlowbiteComponents,
  injectCSS,
  FASTUI_DEFAULT_STYLES,
};

export type {
  FastUIAPI,
  FastUIConfig,
  FastUIPlugin,
  AlpineDirective,
  ChartConfig,
  EChartsOption,
  EChartsInstance,
  FlowbiteComponentType,
  LazyLoadOptions,
  CachedFragment,
} from './types';
