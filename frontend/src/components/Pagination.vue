<script setup>
import { computed } from 'vue'
import { t } from '@/i18n'

const props = defineProps({
  total: {
    type: Number,
    default: 0,
  },
  pageSize: {
    type: Number,
    default: 25,
  },
  modelValue: {
    type: Number,
    default: 1,
  },
})

const emit = defineEmits(['update:modelValue'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

function goPage(page) {
  if (page < 1 || page > totalPages.value) return
  emit('update:modelValue', page)
}
</script>

<template>
  <div class="pagination" v-if="total > pageSize">
    <button class="page-btn" :disabled="modelValue <= 1" @click="goPage(modelValue - 1)">
      {{ t.pagination.prev }}
    </button>
    <span class="page-info">{{ modelValue }} / {{ totalPages }}</span>
    <button class="page-btn" :disabled="modelValue >= totalPages" @click="goPage(modelValue + 1)">
      {{ t.pagination.next }}
    </button>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
}

.page-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--input-radius);
  border: var(--input-border);
  background-color: var(--card-bg);
  color: var(--font-color-primary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  background-color: var(--background-color-hover);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 0.8rem;
  color: var(--font-color-secondary);
  min-width: 60px;
  text-align: center;
}
</style>
