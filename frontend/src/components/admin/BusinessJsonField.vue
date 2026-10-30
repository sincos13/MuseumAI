<script setup>
import { ref, watch } from 'vue'
const props = defineProps({ modelValue: { type: [Object, Array], required: true }, label: String })
const emit = defineEmits(['update:modelValue', 'validity'])
const text = ref(JSON.stringify(props.modelValue, null, 2))
const error = ref('')
let lastValid = JSON.stringify(props.modelValue)
watch(() => props.modelValue, (value) => {
  const serialized = JSON.stringify(value)
  if (serialized !== lastValid) {
    text.value = JSON.stringify(value, null, 2)
    lastValid = serialized
    error.value = ''
    emit('validity', true)
  }
}, { deep: true })
function update(value) {
  text.value = value
  try {
    const parsed = JSON.parse(value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) !== Array.isArray(props.modelValue)) throw new Error()
    lastValid = JSON.stringify(parsed)
    error.value = ''
    emit('update:modelValue', parsed)
    emit('validity', true)
  } catch {
    error.value = 'JSON 格式不正确，修正后才能发布。'
    emit('validity', false)
  }
}
</script>
<template>
  <el-form-item :label="label">
    <el-input :model-value="text" type="textarea" :rows="8" spellcheck="false" @update:model-value="update" />
    <p v-if="error" role="alert" class="json-error">{{ error }}</p>
  </el-form-item>
</template>
<style scoped>.json-error { color: var(--el-color-danger); margin: 8px 0 0; }</style>
