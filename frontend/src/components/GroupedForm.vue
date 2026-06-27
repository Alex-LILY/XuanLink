<script setup>
import { defineProps, defineEmits } from 'vue'
import { t } from '@/i18n'
import IconCheck from '@/components/icons/iconCheck.vue'
import IconCross from '@/components/icons/iconCross.vue'

const props = defineProps({
    groups: {
        type: Array,
        required: true,
        validator: (value) => {
            return value.every(group => {
                return typeof group.name === 'string' &&
                    Array.isArray(group.options) &&
                    group.options.every(option => {
                        return typeof option.id === 'string' &&
                            typeof option.name === 'string' &&
                            typeof option.type === 'string' &&
                            ['text', 'select', 'checkbox'].includes(option.type)
                    })
            })
        }
    },
    modelValue: {
        type: Object,
        required: true
    },
    buttons: {
        type: Array,
        default: () => []
    }
})

const emit = defineEmits(['update:modelValue', 'button-click'])

function updateValue(optionId, value) {
    emit('update:modelValue', optionId, value)
}

function changeClickboxOption(optionId) {
    updateValue(optionId, !props.modelValue[optionId])
}

function onButtonClick(button) {
    emit('button-click', button)
}
</script>

<template>
    <div class="option-group" v-for="group in groups" :key="group.name">
        <div class="options-card">
            <div class="group-header">{{ group.name }}</div>
            <div class="option" v-for="option in group.options" :key="option.id">
                <label class="option-name" :for="'option-' + option.id">
                    {{ option.name }}
                </label>
                <div class="option-control">
                    <input
                        v-if="option.type == 'text'"
                        type="text"
                        :name="option.id"
                        :value="modelValue[option.id]"
                        @input="updateValue(option.id, $event.target.value)"
                        :placeholder="option.placeholder"
                        :id="'option-' + option.id"
                        class="form-input"
                    >
                    <select
                        v-else-if="option.type == 'select'"
                        :name="option.id"
                        :id="'option-' + option.id"
                        :value="modelValue[option.id]"
                        @change="updateValue(option.id, $event.target.value)"
                        class="form-select"
                    >
                        <option
                            v-if="option.default_value === ''"
                            value=""
                            disabled
                        >{{ option.placeholder || t.common.selectPh }}</option>
                        <option
                            v-for="alternative in option.alternatives"
                            :key="alternative.value"
                            :value="alternative.value"
                        >{{ alternative.name }}</option>
                    </select>
                    <div
                        v-else-if="option.type == 'checkbox'"
                        class="input-checkbox"
                        :id="'option-' + option.id"
                        :data-checked="modelValue[option.id]"
                        @click="changeClickboxOption(option.id)"
                    >
                        <input type="hidden" :name="option.id" :value="modelValue[option.id]">
                        <IconCheck v-if="modelValue[option.id]" />
                        <IconCross v-else />
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div v-if="buttons.length > 0" class="submit-buttons-wrapper">
        <div class="submit-buttons">
            <div
                v-for="(button, bIdx) in buttons"
                :key="button.id || bIdx"
                class="submit-button"
                @click="onButtonClick(button)"
            >{{ button.label }}</div>
        </div>
    </div>
</template>

<style scoped>
.option-group {
    display: flex;
    flex-direction: column;
    margin: 0 auto 20px;
    max-width: 900px;
    padding: 0 24px;
}

.options-card {
    background-color: var(--card-bg);
    border: var(--card-border);
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
    backdrop-filter: var(--card-backdrop);
    -webkit-backdrop-filter: var(--card-backdrop);
    overflow: hidden;
}

.group-header {
    color: var(--font-color-secondary);
    font-size: 0.78rem;
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    padding: 11px 20px 9px;
    background-color: var(--table-header-bg);
    border-bottom: 1px solid var(--border-color-grey);
}

.option {
    display: grid;
    grid-template-columns: 160px 1fr;
    align-items: center;
    gap: 16px;
    min-height: var(--table-row-height);
    padding: 10px 20px;
    color: var(--font-color-primary);
    font-size: var(--font-size-base);
    border-bottom: 1px solid var(--border-color-grey);
    transition: background-color var(--transition-fast);
}

.option:last-child {
    border-bottom: none;
}

.option:hover {
    background-color: var(--table-row-hover-bg);
}

.option-name {
    color: var(--font-color-secondary);
    font-weight: var(--font-weight-medium);
    font-size: var(--font-size-base);
    line-height: 1.3;
    cursor: default;
}

.option-control {
    display: flex;
    align-items: center;
}

.form-input,
.form-select {
    height: var(--control-height);
    border-radius: var(--input-radius);
    background-color: var(--input-bg);
    border: var(--input-border);
    color: var(--input-color);
    font-size: var(--font-size-base);
    font-family: var(--font-ui);
    padding: 0 12px;
    outline: none;
    min-width: 0;
    width: 100%;
    max-width: 360px;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-input:focus,
.form-select:focus {
    border-color: var(--input-focus-border-color);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color) 15%, transparent);
}

.form-select option {
    background-color: var(--card-bg);
    color: var(--font-color-primary);
}

.input-checkbox {
    width: 22px;
    height: 22px;
    border-radius: var(--radius-sm);
    background-color: var(--input-bg);
    border: var(--input-border);
    stroke: var(--font-color-secondary);
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    transition: all var(--transition-fast);
    flex-shrink: 0;
}

.input-checkbox:hover {
    background-color: var(--background-color-hover);
}

.input-checkbox[data-checked="true"] {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    stroke: var(--font-color-black);
}

.input-checkbox svg {
    width: 14px;
    height: 14px;
}

.submit-buttons-wrapper {
    max-width: 900px;
    margin: 0 auto;
    padding: 0 24px;
}

.submit-buttons {
    margin: 0 0 24px;
    padding: 18px 24px;
    border-radius: var(--card-radius);
    background-color: var(--card-bg);
    border: var(--card-border);
    box-shadow: var(--card-shadow);
    backdrop-filter: var(--card-backdrop);
    -webkit-backdrop-filter: var(--card-backdrop);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    user-select: none;
}

.submit-button {
    height: var(--button-height);
    min-width: 100px;
    padding: var(--button-padding);
    border-radius: var(--button-radius);
    background: var(--button-bg);
    color: var(--button-color);
    border: var(--button-border, none);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast);
    box-shadow: var(--shadow-button);
}

.submit-button:hover {
    background: var(--button-hover-bg);
    transform: translateY(-1px);
}

.submit-button:active {
    transform: translateY(0);
}

.submit-button:not(:last-child) {
    background: var(--button-secondary-bg);
    color: var(--button-secondary-color);
    border: var(--button-secondary-border, none);
    box-shadow: none;
}

.submit-button:not(:last-child):hover {
    background: var(--button-secondary-hover-bg);
    transform: none;
    box-shadow: none;
}

@media (max-width: 700px) {
    .option-group {
        padding: 0 16px;
    }

    .option {
        grid-template-columns: 1fr;
        gap: 6px;
        align-items: stretch;
        padding: 12px 16px;
    }

    .option-name {
        font-size: 0.8rem;
    }

    .form-input,
    .form-select {
        max-width: 100%;
    }

    .submit-buttons-wrapper {
        padding: 0 16px;
    }

    .submit-buttons {
        margin: 0 0 24px;
        padding: 16px;
        justify-content: center;
    }

    .submit-button {
        flex: 1;
        min-width: 80px;
    }
}
</style>
