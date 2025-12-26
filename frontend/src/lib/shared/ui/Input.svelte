<script lang="ts">
  export let label: string = '';
  export let value: string = '';
  export let placeholder: string = '';
  export let required: boolean = false;
  export let error: string = '';

  let inputId = `input-${Math.random().toString(36).slice(2, 11)}`;
</script>

<div class="input-group">
  {#if label}
    <label class="input-label" for={inputId}>
      {label}
      {#if required}
        <span class="required">*</span>
      {/if}
    </label>
  {/if}
  <input
    id={inputId}
    class="input"
    class:error={!!error}
    type="text"
    {placeholder}
    {required}
    bind:value
    on:input
    on:change
  />
  {#if error}
    <p class="error-text">{error}</p>
  {/if}
</div>

<style>
  .input-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .input-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .required {
    color: var(--color-danger);
  }

  .input {
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  .input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .input.error {
    border-color: var(--color-danger);
  }

  .error-text {
    font-size: 0.75rem;
    color: var(--color-danger);
    margin: 0;
  }
</style>
