import { useAtom } from 'jotai';
import { jetsonIdAtom, mapIdAtom, poseAtom, wsConnectionAtom } from '../state/globalState';
import { View, Text, Image, TouchableOpacity, ScrollView, SafeAreaView, ActivityIndicator } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { useEffect, useState } from 'react';
import axios from "axios";

export default function RegistrationScreen() {
  const [jetsonId, setJetsonId] = useAtom(jetsonIdAtom);
  const [mapId, setMapId] = useAtom(mapIdAtom);
  const [isRegistered, setIsRegistered] = useState(false);
  const [loading, setLoading] = useState(false);
  const [, setPose] = useAtom(poseAtom);
  const [wsConnection, setWsConnection] = useAtom(wsConnectionAtom);

  const handleRegister = () => {
    setLoading(true);
    axios.post("http://10.0.2.2:8000/register", {
        jetson_id: jetsonId,
        map_id: mapId
      })
      .then(()=> setIsRegistered(true))
      .catch(err => console.error(err))
      .finally(()=> setLoading(false));
      
      // open websocket connection
      try{
        // create a websocket object
        const ws = new WebSocket(`ws://10.0.2.2:8000/ws/${jetsonId}`)
        
        // configure the websocket
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          console.log("calling from websocket onmessage", data);
          setPose({x: data.x, y: data.y})
        }
        ws.onopen = () => console.log("Websocket connected")
        ws.onclose = () => console.log("Websocket closed")
        ws.onerror = (err) => console.log("Websocket Error", err)

        setWsConnection(ws);
      } catch(error){
        console.error("Registration failed : ", error);
      }
  }

  const handleTerminate = () => {
    setLoading(true);
    axios.get("http://10.0.2.2:8000/terminate", {
      params: {
        jetson_id: jetsonId
      }
    })
    .then(() => {
      setJetsonId('');
      setMapId('');
      setIsRegistered(false);
    })
    .catch(err => console.error(err))
    .finally(() => setLoading(false));

    try{
      if(wsConnection){
        wsConnection.close(); // close the websocket connection when user terminates the session
        setWsConnection(null);
      }
      
      setPose({x:0, y:0}) // reset the pose

    }catch(error){
      console.error("Termination failed: ", error);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-black">
      <ScrollView className="pb-32" contentContainerStyle={{ flexGrow: 1 }} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View className="w-full items-center justify-center py-4 bg-[#98733c]">
          <Text className="text-xl font-bold text-white">Registration</Text>
          <Image
            source={require('@/assets/images/museum.png')}
            className="h-60"
          />
        </View>

        {/* Welcome Text */}
        <View className="w-full items-center justify-center py-4">
          <Text className="text-[32px] text-[#98733c] font-bold">Welcome!</Text>
          <Text className="text-[16px] py-3">Please select assigned jetson_id and map_id</Text>
        </View>

        {/* Pickers */}
        <View className="mt-10 px-6 space-y-6">
          <View className="border rounded-xl border-gray-400 bg-white/10 dark:bg-black/20">
            <Picker
              selectedValue={jetsonId}
              onValueChange={(itemValue) => setJetsonId(itemValue)}
              enabled={!isRegistered}
              dropdownIconColor="#98733c"
            >
              <Picker.Item label="Select Jetson ID" value="" />
              <Picker.Item label="jetson_01" value="jetson_01" />
              <Picker.Item label="jetson_02" value="jetson_02" />
              <Picker.Item label="jetson_03" value="jetson_03" />
            </Picker>
          </View>
          <View className="h-2" />

          <View className="border rounded-xl border-gray-400 bg-white/10 dark:bg-black/20">
            <Picker
              selectedValue={mapId}
              onValueChange={(itemValue) => setMapId(itemValue)}
              enabled={!isRegistered}
              dropdownIconColor="#98733c"
            >
              <Picker.Item label="Select Map ID" value="" />
              <Picker.Item label="map_01" value="map_01" />
              <Picker.Item label="map_02" value="map_02" />
              <Picker.Item label="map_03" value="map_03" />
            </Picker>
          </View>
        </View>

        {loading && (
          <View className="mt-6 items-center">
            <ActivityIndicator size="large" color="#98733c" />
          </View>
        )}
        
      </ScrollView>


      {/* Fixed Termination Button with Animation */}
      <View className="absolute bottom-4 w-full px-6 space-y-4">
        <TouchableOpacity
          onPress={handleRegister}
          className={`rounded-full py-3 items-center ${isRegistered ? 'bg-gray-400' : 'bg-green-600'}`}
          disabled={isRegistered}
        >
          <Text className="text-white font-semibold">Register Session</Text>
        </TouchableOpacity>
        
        <View className="h-2" />

        <TouchableOpacity
          onPress={handleTerminate}
          className={`rounded-full py-3 items-center ${!isRegistered ? 'bg-gray-400' : 'bg-red-600'}`}
          disabled={!isRegistered}
        >
          <Text className="text-white font-semibold">Terminate Session</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}