import { apiRequest } from './api'

export type CityTier = 'tier1' | 'other'

export interface Room {
  id: string
  house_id: string
  room_name: string
  created_at: string | null
}

export interface House {
  id: string
  city: string
  city_tier: CityTier
  community_name: string | null
  created_at: string | null
  rooms: Room[]
}

export interface HouseCreate {
  city: string
  city_tier: CityTier
  community_name?: string
}

export function fetchHouses(): Promise<{ items: House[]; total: number }> {
  return apiRequest('/houses')
}

export function createHouse(payload: HouseCreate): Promise<House> {
  return apiRequest<House>('/houses', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function deleteHouse(id: string): Promise<{ deleted: boolean }> {
  return apiRequest(`/houses/${id}`, { method: 'DELETE' })
}

export function createRoom(houseId: string, roomName: string): Promise<Room> {
  return apiRequest<Room>(`/houses/${houseId}/rooms`, {
    method: 'POST',
    body: JSON.stringify({ room_name: roomName })
  })
}

export function deleteRoom(houseId: string, roomId: string): Promise<{ deleted: boolean }> {
  return apiRequest(`/houses/${houseId}/rooms/${roomId}`, { method: 'DELETE' })
}
