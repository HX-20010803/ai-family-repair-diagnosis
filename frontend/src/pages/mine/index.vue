<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">我的家庭</h1>
        <p class="app-subtitle">管理房屋和房间，城市能级用于匹配诊断参考价格</p>
      </view>
    </view>

    <view class="panel block active-card">
      <view class="card-title">当前生效家庭</view>
      <view class="card-copy">
        <template v-if="houses.activeHouse">
          {{ houses.activeHouse.city }}{{ houses.activeHouse.community_name ? ' · ' + houses.activeHouse.community_name : '' }} ·
          {{ houses.activeHouse.city_tier === 'tier1' ? '一线城市' : '其他城市' }}
        </template>
        <template v-else>未设置 · 诊断时按默认参考价格</template>
      </view>
      <view class="card-copy muted-copy">H5 阶段使用本地匿名标识，清缓存后房屋数据可能丢失</view>
    </view>

    <view class="panel block">
      <view class="card-title">添加房屋</view>
      <view class="form-row">
        <view class="form-label">城市</view>
        <input :value="newCity" @input="onCityInput" class="form-input" maxlength="32" placeholder="如：深圳" />
      </view>
      <view class="form-row">
        <view class="form-label">城市能级</view>
        <view class="chip-row">
          <button
            v-for="opt in tierOptions"
            :key="opt.value"
            class="chip"
            :class="{ active: newTier === opt.value }"
            type="button"
            @click="newTier = opt.value"
          >{{ opt.label }}</button>
        </view>
      </view>
      <view class="form-row">
        <view class="form-label">小区名（可选）</view>
        <input :value="newCommunity" @input="onCommunityInput" class="form-input" maxlength="40" placeholder="可选" />
      </view>
      <button class="primary-button" type="button" :disabled="!newCity.trim() || submitting" @click="addHouse">添加房屋</button>
    </view>

    <view v-if="houses.loading" class="panel block">
      <view class="card-title">正在加载房屋</view>
    </view>

    <view v-else-if="houses.items.length === 0" class="panel block empty-house">
      <view class="card-copy">还没有房屋，添加后可管理房间并用于价格匹配。</view>
    </view>

    <view v-else class="house-list">
      <view
        v-for="house in houses.items"
        :key="house.id"
        class="panel block house-card"
        :class="{ 'house-active': isActive(house) }"
      >
        <view class="house-head">
          <view>
            <view class="house-title">{{ house.city }}{{ house.community_name ? ' · ' + house.community_name : '' }}</view>
            <view class="house-meta">{{ house.city_tier === 'tier1' ? '一线城市' : '其他城市' }}</view>
          </view>
          <view class="house-tags">
            <view v-if="isActive(house)" class="card-tag active-tag">当前</view>
            <button v-else class="link-button" type="button" @click="houses.setActiveHouse(house)">设为当前</button>
            <button class="link-button" type="button" @click="openHouseEditor(house)">编辑</button>
          </view>
        </view>

        <view class="rooms">
          <view v-for="room in house.rooms" :key="room.id" class="room-chip" @click="openRoomEditor(house.id, room)">
            {{ room.room_name }}
            <text class="room-remove" @click.stop="houses.removeRoom(house.id, room.id)">×</text>
          </view>
          <view v-if="!house.rooms.length" class="card-copy muted-copy">暂无房间</view>
        </view>

        <view class="room-add">
          <view class="quick-chips">
            <button
              v-for="name in quickRooms"
              :key="name"
              class="quick-chip"
              type="button"
              @click="houses.addRoom(house.id, name)"
            >+ {{ name }}</button>
          </view>
          <view class="room-input-row">
            <input
              :value="roomDrafts[house.id] || ''"
              class="form-input room-input"
              maxlength="20"
              placeholder="自定义房间"
              @input="onRoomDraftInput(house.id, $event)"
            />
            <button class="small-button" type="button" :disabled="!(roomDrafts[house.id] || '').trim()" @click="addCustomRoom(house.id)">添加</button>
          </view>
        </view>

        <button class="danger-button" type="button" @click="removeHouse(house.id)">删除房屋</button>
      </view>
    </view>

    <view v-if="editing" class="edit-overlay" @click.self="cancelEdit">
      <view class="edit-modal">
        <view class="edit-modal-title">{{ editingTitle }}</view>

        <template v-if="editingTarget?.type === 'house'">
          <view class="form-row compact-row">
            <view class="form-label">城市</view>
            <input :value="editHouseForm.city" class="edit-modal-input" maxlength="32" placeholder="如：深圳" @input="onEditHouseCityInput" />
          </view>
          <view class="form-row compact-row">
            <view class="form-label">城市能级</view>
            <view class="chip-row">
              <button
                v-for="opt in tierOptions"
                :key="opt.value"
                class="chip"
                :class="{ active: editHouseForm.city_tier === opt.value }"
                type="button"
                @click="editHouseForm.city_tier = opt.value"
              >{{ opt.label }}</button>
            </view>
          </view>
          <view class="form-row compact-row">
            <view class="form-label">小区名（可选）</view>
            <input :value="editHouseForm.community_name" class="edit-modal-input" maxlength="40" placeholder="可选" @input="onEditHouseCommunityInput" />
          </view>
        </template>

        <template v-else>
          <input :value="editingValue" class="edit-modal-input" :maxlength="64" placeholder="房间名" @input="onEditValueInput" @confirm="saveEdit" />
        </template>

        <view class="edit-modal-actions">
          <button class="edit-modal-btn cancel" type="button" @click="cancelEdit">取消</button>
          <button class="edit-modal-btn confirm" type="button" :disabled="!canSaveEdit || saving" @click="saveEdit">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useHousesStore } from '../../stores/houses'
import type { CityTier, House } from '../../services/houses'

const houses = useHousesStore()
const submitting = ref(false)

const newCity = ref('')
const newTier = ref<CityTier>('other')
const newCommunity = ref('')
const roomDrafts = reactive<Record<string, string>>({})

const editing = ref(false)
const editingTitle = ref('')
const editingValue = ref('')
const editingTarget = ref<{ type: 'house' | 'room'; houseId?: string; id: string } | null>(null)
const editHouseForm = reactive<{ city: string; city_tier: CityTier; community_name: string }>({
  city: '',
  city_tier: 'other',
  community_name: ''
})
const saving = ref(false)

const tierOptions = [
  { label: '一线城市', value: 'tier1' as const },
  { label: '其他城市', value: 'other' as const }
]

const quickRooms = ['厨房', '卫生间', '客厅', '卧室', '阳台', '入户门']

const canSaveEdit = computed(() => {
  const target = editingTarget.value
  if (!target) return false
  if (target.type === 'house') return Boolean(editHouseForm.city.trim())
  return Boolean(editingValue.value.trim())
})

function inputValue(e: any) {
  return String(e.detail?.value ?? e.target?.value ?? '')
}

function onCityInput(e: any) {
  newCity.value = inputValue(e)
}
function onCommunityInput(e: any) {
  newCommunity.value = inputValue(e)
}
function onRoomDraftInput(houseId: string, e: any) {
  roomDrafts[houseId] = inputValue(e)
}
function onEditValueInput(e: any) {
  editingValue.value = inputValue(e)
}
function onEditHouseCityInput(e: any) {
  editHouseForm.city = inputValue(e)
}
function onEditHouseCommunityInput(e: any) {
  editHouseForm.community_name = inputValue(e)
}

function isActive(house: House): boolean {
  return houses.activeHouseId === house.id
}

async function addHouse() {
  if (!newCity.value.trim() || submitting.value) return
  submitting.value = true
  try {
    const house = await houses.addHouse({
      city: newCity.value.trim(),
      city_tier: newTier.value,
      community_name: newCommunity.value.trim()
    })
    houses.setActiveHouse(house)
    newCity.value = ''
    newCommunity.value = ''
    uni.showToast({ title: '已添加', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '添加失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

async function removeHouse(id: string) {
  uni.showModal({
    title: '删除房屋',
    content: '将同时删除该房屋下的所有房间，确定吗？',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await houses.removeHouse(id)
        uni.showToast({ title: '已删除', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error instanceof Error ? error.message : '删除失败', icon: 'none' })
      }
    }
  })
}

async function addCustomRoom(houseId: string) {
  const name = (roomDrafts[houseId] || '').trim()
  if (!name) return
  try {
    await houses.addRoom(houseId, name)
    roomDrafts[houseId] = ''
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '添加失败', icon: 'none' })
  }
}

function openHouseEditor(house: House) {
  editingTarget.value = { type: 'house', id: house.id }
  editingTitle.value = '编辑房屋'
  editHouseForm.city = house.city
  editHouseForm.city_tier = house.city_tier
  editHouseForm.community_name = house.community_name || ''
  editing.value = true
}

function openRoomEditor(houseId: string, room: { id: string; room_name: string }) {
  editingTarget.value = { type: 'room', houseId, id: room.id }
  editingTitle.value = '修改房间名'
  editingValue.value = room.room_name
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editingTarget.value = null
}

async function saveEdit() {
  const target = editingTarget.value
  if (!target || !canSaveEdit.value || saving.value) return
  saving.value = true
  try {
    if (target.type === 'house') {
      await houses.editHouse(target.id, {
        city: editHouseForm.city.trim(),
        city_tier: editHouseForm.city_tier,
        community_name: editHouseForm.community_name.trim()
      })
    } else if (target.houseId) {
      await houses.editRoom(target.houseId, target.id, editingValue.value.trim())
    }
    uni.showToast({ title: '已修改', icon: 'success' })
    editing.value = false
    editingTarget.value = null
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '修改失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  houses.fetchList()
})
</script>

<style scoped>
.block {
  padding: 14px;
}

.active-card {
  border-color: var(--color-primary);
  background: var(--color-surface-soft);
}

.house-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.house-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.house-active {
  border-color: var(--color-primary);
}

.house-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.house-title {
  font-size: 16px;
  font-weight: 780;
}

.house-meta {
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.3;
}

.house-tags {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}

.card-tag {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-soft);
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 700;
}

.active-tag {
  background: var(--color-primary);
  color: #fff;
}

.link-button {
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-primary-strong);
  font-size: 12px;
}

.link-button::after {
  border: 0;
}

.rooms {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.room-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-soft);
  color: var(--color-text);
  font-size: 13px;
}

.room-remove {
  color: var(--color-muted);
  font-size: 15px;
  font-weight: 700;
  padding-left: 2px;
}

.room-add {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-chip {
  padding: 5px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-primary-strong);
  font-size: 12px;
}

.quick-chip::after {
  border: 0;
}

.room-input-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.room-input {
  flex: 1;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.compact-row {
  margin-bottom: 9px;
}

.form-label {
  font-size: 13px;
  font-weight: 700;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 14px;
}

.chip-row {
  display: flex;
  gap: 8px;
}

.chip {
  padding: 7px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.chip::after {
  border: 0;
}

.chip.active {
  border-color: var(--color-primary);
  background: var(--color-surface-soft);
  color: var(--color-primary-strong);
}

.primary-button {
  width: 100%;
  margin-top: 4px;
  padding: 12px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 750;
}

.primary-button::after {
  border: 0;
}

.primary-button[disabled] {
  opacity: 0.6;
}

.small-button {
  padding: 0 14px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.small-button::after {
  border: 0;
}

.small-button[disabled] {
  opacity: 0.6;
}

.danger-button {
  align-self: flex-start;
  padding: 6px 14px;
  border: 1px solid #f0b7ad;
  border-radius: var(--radius-md);
  background: #fff7f6;
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 600;
}

.danger-button::after {
  border: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 780;
}

.card-copy {
  margin-top: 6px;
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.5;
}

.muted-copy {
  color: var(--color-muted);
}

.empty-house {
  text-align: center;
}

.edit-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.edit-modal {
  width: 84%;
  max-width: 340px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 18px 16px 14px;
  box-shadow: var(--shadow-soft);
}

.edit-modal-title {
  font-size: 16px;
  font-weight: 780;
  margin-bottom: 12px;
  text-align: center;
}

.edit-modal-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  font-size: 15px;
}

.edit-modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.edit-modal-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 700;
}

.edit-modal-btn::after {
  border: 0;
}

.edit-modal-btn.cancel {
  background: var(--color-surface-soft);
  color: var(--color-muted);
}

.edit-modal-btn.confirm {
  background: var(--color-primary);
  color: #fff;
}

.edit-modal-btn.confirm[disabled] {
  opacity: 0.6;
}

/* uni-app H5 renders <input> as <uni-input><input class="uni-input-input">.
   The inner input can collapse to 0px height unless the wrapper has an explicit height. */
.form-input,
.edit-modal-input {
  min-height: 40px;
  height: 40px;
  line-height: 40px;
  padding-top: 0;
  padding-bottom: 0;
}

.form-input :deep(.uni-input-wrapper),
.form-input :deep(.uni-input-input),
.edit-modal-input :deep(.uni-input-wrapper),
.edit-modal-input :deep(.uni-input-input) {
  width: 100%;
  height: 100%;
  line-height: 40px;
}
</style>
