<template>
  <div class="sms-code-input">
    <div class="sms-code-input__boxes">
      <input
        v-for="(_, index) in digits"
        :key="index"
        :ref="(el) => setInputRef(el as HTMLInputElement, index)"
        type="text"
        inputmode="numeric"
        maxlength="1"
        class="sms-code-input__box"
        :class="{ 'sms-code-input__box--filled': digits[index] !== '' }"
        :value="digits[index]"
        @input="handleInput(index, $event)"
        @keydown="handleKeydown(index, $event)"
        @paste="handlePaste($event)"
        @focus="handleFocus(index)"
        autocomplete="one-time-code"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const CODE_LENGTH = 6

interface Props {
  modelValue: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  complete: [value: string]
}>()

const digits = ref<string[]>(Array(CODE_LENGTH).fill(''))
const inputRefs = ref<(HTMLInputElement | null)[]>(Array(CODE_LENGTH).fill(null))

function setInputRef(el: HTMLInputElement | null, index: number) {
  inputRefs.value[index] = el
}

function focusInput(index: number) {
  nextTick(() => {
    const input = inputRefs.value[index]
    if (input) {
      input.focus()
      input.select()
    }
  })
}

function updateModelValue() {
  const value = digits.value.join('')
  emit('update:modelValue', value)
  if (value.length === CODE_LENGTH && digits.value.every((d) => d !== '')) {
    emit('complete', value)
  }
}

function handleInput(index: number, event: Event) {
  const target = event.target as HTMLInputElement
  const value = target.value

  // Only allow digits
  if (value && !/^\d$/.test(value)) {
    target.value = digits.value[index] ?? ''
    return
  }

  digits.value[index] = value
  updateModelValue()

  // Move to next input on valid digit entry
  if (value && index < CODE_LENGTH - 1) {
    focusInput(index + 1)
  }
}

function handleKeydown(index: number, event: KeyboardEvent) {
  if (event.key === 'Backspace') {
    if (digits.value[index] === '' && index > 0) {
      // If current box is empty, move back and clear previous
      digits.value[index - 1] = ''
      updateModelValue()
      focusInput(index - 1)
      event.preventDefault()
    } else {
      // Clear current box
      digits.value[index] = ''
      updateModelValue()
    }
  } else if (event.key === 'ArrowLeft' && index > 0) {
    focusInput(index - 1)
    event.preventDefault()
  } else if (event.key === 'ArrowRight' && index < CODE_LENGTH - 1) {
    focusInput(index + 1)
    event.preventDefault()
  }
}

function handlePaste(event: ClipboardEvent) {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  const cleanDigits = pastedText.replace(/\D/g, '').slice(0, CODE_LENGTH)

  if (cleanDigits.length === 0) return

  for (let i = 0; i < CODE_LENGTH; i++) {
    digits.value[i] = i < cleanDigits.length ? (cleanDigits[i] ?? '') : ''
  }

  updateModelValue()

  // Focus the next empty box or the last box
  const nextEmpty = digits.value.findIndex((d) => d === '')
  focusInput(nextEmpty === -1 ? CODE_LENGTH - 1 : nextEmpty)
}

function handleFocus(index: number) {
  const input = inputRefs.value[index]
  if (input) {
    input.select()
  }
}

// Sync external modelValue changes to internal digits
watch(
  () => props.modelValue,
  (newVal) => {
    const chars = (newVal || '').split('')
    for (let i = 0; i < CODE_LENGTH; i++) {
      digits.value[i] = chars[i] || ''
    }
  },
  { immediate: true }
)

defineExpose({
  /** Focus the first input box */
  focus: () => focusInput(0),
  /** Clear all digits */
  clear: () => {
    digits.value = Array(CODE_LENGTH).fill('')
    updateModelValue()
    focusInput(0)
  },
})
</script>

<style lang="scss" scoped>
.sms-code-input {
  &__boxes {
    display: flex;
    gap: 10px;
    justify-content: center;
  }

  &__box {
    width: 46px;
    height: 54px;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    text-align: center;
    font-size: 1.375rem;
    font-weight: 600;
    color: var(--color-text-primary);
    background-color: var(--color-bg-primary);
    caret-color: var(--color-primary);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    outline: none;

    &:focus {
      border-color: var(--color-primary);
      box-shadow: 0 0 0 3px rgba(0, 61, 165, 0.15);
    }

    &--filled {
      border-color: var(--color-primary);
      background-color: var(--color-primary-lighter);
    }

    // Hide number input spinners
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
  }
}

@media (max-width: 480px) {
  .sms-code-input {
    &__boxes {
      gap: 6px;
    }

    &__box {
      width: 40px;
      height: 48px;
      font-size: 1.25rem;
    }
  }
}
</style>
