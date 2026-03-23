/**
 * FastUI Type Definitions
 * Server-Driven Interactivity (SDI) for FastStack
 */

declare global {
  interface Window {
    FastUI: FastUIAPI;
    Alpine: AlpineAPI;
    htmx: HTMXAPI;
    echarts: EChartsAPI;
  }
}

/**
 * FastUI Global API
 */
export interface FastUIAPI {
  version: string;
  debug: boolean;
  
  /** Global reactive store */
  store: FastUIStore;
  
  /** Fragment cache */
  cache: FastUICache;
  
  /** Plugin registry */
  plugins: Map<string, FastUIPlugin>;
  
  /** Directive registry */
  directives: Map<string, AlpineDirective>;
  
  /** Initialize FastUI */
  init(): void;
  
  /** Register a plugin */
  registerPlugin(name: string, plugin: FastUIPlugin): void;
  
  /** Register a custom directive */
  registerDirective(name: string, directive: AlpineDirective): void;
  
  /** Reinitialize components in a DOM element */
  reinit(el: HTMLElement): void;
  
  /** Lazy load a module */
  lazyLoad(module: string): Promise<void>;
  
  /** Create ECharts instance */
  createChart(el: HTMLElement, options: EChartsOption): Promise<EChartsInstance>;
  
  /** Initialize Flowbite component */
  initFlowbite(el: HTMLElement, type: string): void;
}

/**
 * Global reactive store (Alpine store wrapper)
 */
export interface FastUIStore {
  /** Get a value from the store */
  get(key: string): unknown;
  
  /** Set a value in the store */
  set(key: string, value: unknown): void;
  
  /** Delete a value from the store */
  delete(key: string): void;
  
  /** Clear all values */
  clear(): void;
  
  /** Subscribe to changes */
  subscribe(key: string, callback: (value: unknown) => void): () => void;
}

/**
 * Fragment cache for HTMX responses
 */
export interface FastUICache {
  /** Get cached fragment */
  get(key: string): CachedFragment | null;
  
  /** Cache a fragment */
  set(key: string, fragment: CachedFragment): void;
  
  /** Remove a cached fragment */
  delete(key: string): void;
  
  /** Clear all cached fragments */
  clear(): void;
  
  /** Check if fragment exists */
  has(key: string): boolean;
}

export interface CachedFragment {
  html: string;
  timestamp: number;
  ttl: number;
}

/**
 * FastUI Plugin Interface
 */
export interface FastUIPlugin {
  name: string;
  version?: string;
  install(api: FastUIAPI): void;
  uninstall?(): void;
}

/**
 * Alpine.js Directive Interface
 */
export interface AlpineDirective {
  name: string;
  callback: (el: HTMLElement, value: string, effect: () => void) => void;
}

/**
 * Alpine.js API (simplified)
 */
export interface AlpineAPI {
  data(name: string, callback: () => object): void;
  store(name: string, value: object): void;
  directive(name: string, callback: (el: HTMLElement, value: string, effect: () => void) => void): void;
  magic(name: string, callback: (el: HTMLElement) => unknown): void;
  start(): void;
  initTree(el: HTMLElement): void;
}

/**
 * HTMX API (simplified)
 */
export interface HTMXAPI {
  on(event: string, callback: (evt: Event) => void): void;
  off(event: string, callback: (evt: Event) => void): void;
  trigger(el: HTMLElement, event: string, detail?: object): void;
  process(el: HTMLElement): void;
  ajax(verb: string, path: string, options: object): void;
}

/**
 * ECharts Option Interface
 */
export interface EChartsOption {
  title?: { text?: string; subtext?: string };
  tooltip?: object;
  legend?: object;
  xAxis?: object;
  yAxis?: object;
  series?: object[];
  grid?: object;
  color?: string[];
  [key: string]: unknown;
}

/**
 * ECharts Instance Interface
 */
export interface EChartsInstance {
  setOption(option: EChartsOption): void;
  resize(): void;
  dispose(): void;
  on(event: string, callback: (params: unknown) => void): void;
  off(event: string, callback?: (params: unknown) => void): void;
}

/**
 * ECharts API (simplified)
 */
export interface EChartsAPI {
  init(el: HTMLElement, theme?: string): EChartsInstance;
  dispose(el: HTMLElement): void;
  getInstanceByDom(el: HTMLElement): EChartsInstance | null;
}

/**
 * Chart Directive Configuration
 */
export interface ChartConfig extends EChartsOption {
  /** Lazy load chart when visible */
  lazy?: boolean;
  
  /** Responsive resize */
  responsive?: boolean;
  
  /** Theme name */
  theme?: string;
  
  /** Chart height */
  height?: string | number;
  
  /** Chart width */
  width?: string | number;
  
  /** Auto-update from data source */
  dataSource?: string;
  
  /** Refresh interval in ms */
  refreshInterval?: number;
}

/**
 * Flowbite Component Types
 */
export type FlowbiteComponentType = 
  | 'accordion'
  | 'carousel'
  | 'collapse'
  | 'dropdown'
  | 'modal'
  | 'tabs'
  | 'tooltip'
  | 'popover'
  | 'drawer'
  | 'dismiss';

/**
 * Lazy Load Options
 */
export interface LazyLoadOptions {
  /** Root margin for intersection observer */
  rootMargin?: string;
  
  /** Threshold for triggering */
  threshold?: number;
  
  /** Trigger once or every time */
  triggerOnce?: boolean;
  
  /** Callback when element is visible */
  onVisible?: (el: HTMLElement) => void;
  
  /** Callback when element is hidden */
  onHidden?: (el: HTMLElement) => void;
}

/**
 * FastUI Configuration
 */
export interface FastUIConfig {
  /** Enable debug mode */
  debug?: boolean;
  
  /** Enable fragment caching */
  cacheEnabled?: boolean;
  
  /** Default TTL for cached fragments (ms) */
  cacheTTL?: number;
  
  /** Lazy load ECharts */
  lazyLoadECharts?: boolean;
  
  /** Lazy load Flowbite */
  lazyLoadFlowbite?: boolean;
  
  /** Auto-reinit after HTMX swaps */
  autoReinit?: boolean;
  
  /** Tailwind CSS CDN URL */
  tailwindCDN?: string;
}

export {};
