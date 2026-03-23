/**
 * FastUI x-chart Directive
 * Alpine.js directive for ECharts integration
 */

import type { ChartConfig, EChartsInstance } from '../types';
import { debugLog, generateId, hasECharts, safeParseJSON } from '../utils/helpers';

/**
 * Chart instances registry for cleanup and resize
 */
const chartInstances = new Map<string, EChartsInstance>();

/**
 * Resize observer for responsive charts
 */
let resizeObserver: ResizeObserver | null = null;

/**
 * Initialize the resize observer
 */
function initResizeObserver(): void {
  if (resizeObserver) return;

  resizeObserver = new ResizeObserver((entries) => {
    entries.forEach((entry) => {
      const chartId = (entry.target as HTMLElement).dataset.chartId;
      if (chartId) {
        const instance = chartInstances.get(chartId);
        instance?.resize();
      }
    });
  });
}

/**
 * Create x-chart Alpine directive
 */
export function createChartDirective() {
  return {
    name: 'chart',

    callback(el: HTMLElement, value: string): void {
      // Generate unique ID for this chart
      const chartId = generateId('chart');
      el.dataset.chartId = chartId;

      // Parse configuration
      let config: ChartConfig = {};

      // Try to get config from attribute value
      if (value) {
        // Check if it's a JSON string
        if (value.startsWith('{') || value.startsWith('[')) {
          config = safeParseJSON(value, {});
        } else {
          // Try to get from window or Alpine data
          const alpineData = (el as unknown as { __x?: { $data: Record<string, unknown> } }).__x?.$data;
          if (alpineData && alpineData[value]) {
            config = alpineData[value] as ChartConfig;
          }
        }
      }

      // Also check for data-chart-config attribute
      const configAttr = el.dataset.chartConfig;
      if (configAttr) {
        const parsedConfig = safeParseJSON(configAttr, {});
        config = { ...config, ...parsedConfig };
      }

      // Set dimensions
      if (config.height) {
        el.style.height = typeof config.height === 'number' 
          ? `${config.height}px` 
          : config.height;
      }
      if (config.width) {
        el.style.width = typeof config.width === 'number' 
          ? `${config.width}px` 
          : config.width;
      }

      // Check for lazy loading
      if (config.lazy !== false) {
        el.dataset.lazyChart = 'true';
      }

      // Initialize chart
      const initChart = async () => {
        // Wait for ECharts to be available
        if (!hasECharts()) {
          debugLog('ECharts not loaded, skipping chart init');
          return;
        }

        try {
          // Dispose existing instance if any
          const existingInstance = window.echarts.getInstanceByDom(el);
          if (existingInstance) {
            existingInstance.dispose();
          }

          // Create new instance
          const instance = window.echarts.init(el, config.theme);
          chartInstances.set(chartId, instance);

          // Set options
          const { lazy, responsive, theme, height, width, dataSource, refreshInterval, ...chartOptions } = config;
          instance.setOption(chartOptions);

          // Setup resize observer for responsive charts
          if (config.responsive !== false) {
            initResizeObserver();
            resizeObserver?.observe(el);
          }

          // Setup auto-refresh if configured
          if (refreshInterval && refreshInterval > 0) {
            setInterval(async () => {
              if (dataSource) {
                try {
                  const response = await fetch(dataSource);
                  const data = await response.json();
                  instance.setOption(data);
                } catch (e) {
                  debugLog('Failed to refresh chart data', e);
                }
              }
            }, refreshInterval);
          }

          debugLog(`Chart initialized: ${chartId}`);
        } catch (e) {
          console.error('[FastUI] Failed to initialize chart:', e);
        }
      };

      // Initialize immediately or lazy load
      if (!config.lazy) {
        initChart();
      } else {
        // Use Intersection Observer for lazy loading
        const observer = new IntersectionObserver(
          (entries, obs) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                initChart();
                obs.unobserve(entry.target);
              }
            });
          },
          { threshold: 0.1 }
        );
        observer.observe(el);
      }

      // Cleanup on element removal
      const cleanup = () => {
        const instance = chartInstances.get(chartId);
        if (instance) {
          instance.dispose();
          chartInstances.delete(chartId);
        }
        resizeObserver?.unobserve(el);
      };

      // Use MutationObserver to detect removal
      const mutationObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.removedNodes.forEach((node) => {
            if (node === el || (node as Element).contains?.(el)) {
              cleanup();
            }
          });
        });
      });

      mutationObserver.observe(document.body, { childList: true, subtree: true });
    },
  };
}

/**
 * Update chart data
 */
export function updateChart(chartId: string, options: Record<string, unknown>): void {
  const instance = chartInstances.get(chartId);
  if (instance) {
    instance.setOption(options);
  }
}

/**
 * Get chart instance
 */
export function getChartInstance(chartId: string): EChartsInstance | undefined {
  return chartInstances.get(chartId);
}

/**
 * Dispose chart
 */
export function disposeChart(chartId: string): void {
  const instance = chartInstances.get(chartId);
  if (instance) {
    instance.dispose();
    chartInstances.delete(chartId);
  }
}

/**
 * Resize all charts
 */
export function resizeAllCharts(): void {
  chartInstances.forEach((instance) => {
    instance.resize();
  });
}

// Resize charts on window resize
if (typeof window !== 'undefined') {
  window.addEventListener('resize', () => {
    resizeAllCharts();
  });
}
