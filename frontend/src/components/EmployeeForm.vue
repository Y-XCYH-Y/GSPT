<template>
  <div class="modal" :class="{ active: visible }" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ isEdit ? '编辑员工' : '添加员工' }}</h2>
        <span class="close" @click="$emit('close')">&times;</span>
      </div>
      
      <form @submit.prevent="handleSubmit" class="employee-form">
        <div class="form-row">
          <div class="form-group">
            <label>姓名 *</label>
            <input v-model="form.name" class="input" required />
          </div>
          <div class="form-group">
            <label>人员编号</label>
            <input v-model="form.employee_id" class="input" placeholder="如：A001" />
          </div>
          <div class="form-group">
            <label>性别 *</label>
            <select v-model="form.gender" class="input" required>
              <option value="">请选择</option>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </div>
        </div>

        <div class="form-row" v-if="!isEdit">
          <div class="form-group">
            <label>用户名 *</label>
            <input v-model="form.username" class="input" required />
          </div>
          <div class="form-group">
            <label>密码 *</label>
            <input v-model="form.password" type="password" class="input" required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>专业方向 *</label>
            <select v-model="form.profession" class="input" required>
              <option value="">请选择</option>
              <option v-for="p in professions" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>职称情况</label>
            <input v-model="form.title" class="input" placeholder="如：高级工程师" />
          </div>
        </div>

        <div class="form-group">
          <label>注册情况</label>
          <input v-model="form.registration" class="input" placeholder="如：一级注册建筑师" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>出生年月</label>
            <input v-model="form.birth_date" type="month" class="input" />
          </div>
          <div class="form-group">
            <label>参加工作时间</label>
            <input v-model="form.work_start_date" type="month" class="input" />
          </div>
        </div>

        <div class="form-group">
          <label>擅长项目类型（多选）</label>
          <div class="checkbox-group">
            <label v-for="pt in projectTypes" :key="pt" class="checkbox-item">
              <input type="checkbox" :value="pt" v-model="form.project_types" />
              {{ pt }}
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>历史项目经验</label>
          <textarea v-model="form.experience" class="input" rows="3" placeholder="描述参与过的项目及角色"></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>是否驻外</label>
            <select v-model="form.is_field" class="input">
              <option value="否">否</option>
              <option value="是">是</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>备注</label>
          <input v-model="form.remark" class="input" placeholder="其他补充信息" />
        </div>

        <div class="form-actions">
          <button type="button" class="btn" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary">{{ isEdit ? '保存修改' : '添加员工' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  isEdit: Boolean,
  employeeData: Object,
  professions: Array,
  projectTypes: Array,
})

const emit = defineEmits(['close', 'save'])

const form = reactive({
  username: '',
  employee_id: '',
  password: '',
  name: '',
  gender: '',
  profession: '',
  registration: '',
  title: '',
  birth_date: '',
  work_start_date: '',
  project_types: [],
  experience: '',
  is_field: '否',
  current_load: '空闲',
  occupancy_rate: 0,
  remark: ''
})

watch(() => props.employeeData, (val) => {
  if (props.visible && props.isEdit && val) {
    Object.assign(form, {
      username: val.username || '',
      password: '',
      name: val.name || '',
      employee_id: val.employee_id || '',
      gender: val.gender || '',
      profession: val.profession || '',
      registration: val.registration || '',
      title: val.title || '',
      birth_date: val.birth_date || '',
      work_start_date: val.work_start_date || '',
      project_types: val.project_types || [],
      experience: val.experience || '',
      is_field: val.is_field || '否',
      current_load: val.current_load || '空闲',
      occupancy_rate: val.occupancy_rate || 0,
      remark: val.remark || ''
    })
  } else if (props.visible && !props.isEdit) {
    Object.assign(form, {
      username: '', password: '', name: '', gender: '',
      profession: '', registration: '', title: '',
      birth_date: '', work_start_date: '', project_types: [],
      experience: '', is_field: '否', current_load: '空闲',
      occupancy_rate: 0, remark: ''
    })
  }
}, { immediate: true })

function handleSubmit() {
  emit('save', { ...form })
}
</script>

<style scoped>
.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
.modal.active { display: flex; }
.modal-content { background: white; padding: 30px; border-radius: 16px; width: 90%; max-width: 700px; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.close { font-size: 28px; cursor: pointer; color: #999; }
.close:hover { color: #333; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; margin-bottom: 4px; font-size: 13px; font-weight: 500; color: #374151; }
.checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; }
.checkbox-item { display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; }
.form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; padding-top: 16px; border-top: 1px solid #e5e7eb; }
@media (max-width: 600px) { .form-row { grid-template-columns: 1fr; } }
</style>