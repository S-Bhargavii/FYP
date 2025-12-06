# SLAM-based Visual Localisation System

This repository contains the **backend and frontend components** of a SLAM-based visual localisation system.
The system integrates a Jetson-based ORB-SLAM3 localisation engine with a backend server and a mobile client for real-time pose tracking, visualisation and navigation guidance.

For the ORB-SLAM3 implementation and the MQTT jetson client used in this system, please refer to:
[https://github.com/S-Bhargavii/ORB_SLAM3/tree/master](https://github.com/S-Bhargavii/ORB_SLAM3/tree/master)

---

## System Architecture Overview

* **Device Layer**: NVIDIA Jetson running ORB-SLAM3 and publishing pose data via MQTT
* **Backend Server**: FastAPI-based service handling communication, pose storage, and APIs
* **Frontend Application**: Mobile application built using React Native.
  
---

## Backend Setup

The backend server is implemented using **FastAPI** and communicates with the Jetson device using **MQTT**.
Redis is used for fast, real-time data storage.

### Setup Instructions

Navigate to the backend directory:

```bash
cd backend
```

Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend server:

```bash
uvicorn server:app --reload
```

---

### Required Services

Ensure the following services are running on the **same machine as the backend**:

* Redis Server
* Mosquitto MQTT Broker

Example (Ubuntu):

```bash
sudo systemctl start redis
sudo systemctl start mosquitto
```

---

### Backend Configuration

Update the configuration values in `constants.py`:

* **MQTT Broker IP**
  Replace `MQTT_BROKER` with the IP address of the machine running the Mosquitto broker.

* **JWT Secret Key**
  Replace `SECRET_KEY` with a secure **256-bit secret key** for JWT authentication.

Configuration file:
[https://github.com/S-Bhargavii/FYP/blob/main/backend/constants.py](https://github.com/S-Bhargavii/FYP/blob/main/backend/constants.py)

---

## Frontend Setup

The frontend is a **React Native mobile application** built using **Expo**.

### Prerequisites

* Node.js (v16+ recommended)
* npm or yarn
* Expo CLI

Install Expo CLI (if not already installed):

```bash
npm install -g expo-cli
```

---

### Setup Instructions

Navigate to the mobile application directory:

```bash
cd mobile-app
```

Install dependencies:

```bash
npm install
```

Start the Expo development server:

```bash
npx expo start
```

You can then run the app on:

* Expo Go (physical device)
* Android emulator
* iOS simulator

---

## Notes

* The backend and frontend must be able to reach the same MQTT broker.
* The Jetson device publishes pose updates via MQTT, which are consumed by the backend.
* This repository focuses on server-side and client-side integration; SLAM execution occurs on the Jetson device.

---

## Related Repositories

* ORB-SLAM3 (Jetson implementation):
  [https://github.com/S-Bhargavii/ORB_SLAM3](https://github.com/S-Bhargavii/ORB_SLAM3)
