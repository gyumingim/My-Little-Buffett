<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let text: string = '';
</script>

<div class="loading-container">
  <div class="spinner spinner-{size}"></div>
  {#if text}
    <p class="loading-text">{text}</p>
  {/if}
</div>

<style>
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    gap: 1rem;
  }

  .spinner {
    border: 4px solid var(--border-color);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .spinner-sm {
    width: 24px;
    height: 24px;
    border-width: 2px;
  }

  .spinner-md {
    width: 40px;
    height: 40px;
    border-width: 4px;
  }

  .spinner-lg {
    width: 56px;
    height: 56px;
    border-width: 5px;
  }

  .loading-text {
    color: var(--text-secondary);
    font-size: 0.875rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
