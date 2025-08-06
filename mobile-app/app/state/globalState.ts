// keeping track of the global state 
import { atom } from 'jotai';

// store the jetson id
export const jetsonIdAtom = atom<string>('');

// store the map id 
export const mapIdAtom = atom<string>('');

// Pose Data Atom (Global Live Position)
export const poseAtom = atom({ x: 0, y: 0 });

// WebSocket Connection Atom (store the connection instance)
export const wsConnectionAtom = atom<WebSocket | null>(null);