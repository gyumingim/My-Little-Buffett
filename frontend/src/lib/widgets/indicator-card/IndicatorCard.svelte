<script lang="ts">
  import { signalToKorean, signalToClass } from '$shared/utils';

  export let name: string;
  export let description: string;
  export let signal: string;
  export let signalDescription: string;
  export let metrics: Array<{ label: string; value: string }> = [];
</script>

<div class="indicator-card">
  <div class="indicator-header">
    <div class="indicator-info">
      <h4 class="indicator-name">{name}</h4>
      <p class="indicator-desc">{description}</p>
    </div>
    <span class="signal-badge {signalToClass(signal)}">
      {signalToKorean(signal)}
    </span>
  </div>

  <div class="indicator-metrics">
    {#each metrics as metric}
      <div class="metric">
        <span class="metric-label">{metric.label}</span>
        <span class="metric-value">{metric.value}</span>
      </div>
    {/each}
  </div>

  <p class="signal-description">{signalDescription}</p>
</div>

<style>
  .indicator-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .indicator-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .indicator-name {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .indicator-desc {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0.25rem 0 0;
  }

  .signal-badge {
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .indicator-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
    padding: 1rem;
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .metric-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .metric-value {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .signal-description {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.5;
  }
</style>
