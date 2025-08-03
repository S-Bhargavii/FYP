import { useAtom } from 'jotai';
import { jetsonIdAtom, mapIdAtom } from '../state/globalState';
import { View, Text, Image, TouchableOpacity, ScrollView, SafeAreaView } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import Animated, { FadeInUp } from 'react-native-reanimated';

export default function RegistrationScreen() {
  const [jetsonId, setJetsonId] = useAtom(jetsonIdAtom);
  const [mapId, setMapId] = useAtom(mapIdAtom);

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
              dropdownIconColor="#98733c"
            >
              <Picker.Item label="Select Jetson ID" value="" />
              <Picker.Item label="jetson_01" value="jetson_01" />
              <Picker.Item label="jetson_02" value="jetson_02" />
              <Picker.Item label="jetson_03" value="jetson_03" />
            </Picker>
          </View>

          <View className="border rounded-xl border-gray-400 bg-white/10 dark:bg-black/20">
            <Picker
              selectedValue={mapId}
              onValueChange={(itemValue) => setMapId(itemValue)}
              dropdownIconColor="#98733c"
            >
              <Picker.Item label="Select Map ID" value="" />
              <Picker.Item label="map_01" value="map_01" />
              <Picker.Item label="map_02" value="map_02" />
              <Picker.Item label="map_03" value="map_03" />
            </Picker>
          </View>
        </View>
      </ScrollView>

      {/* Fixed Termination Button with Animation */}
      {jetsonId && mapId ? (
        <Animated.View entering={FadeInUp} className="absolute bottom-4 w-full px-6">
          <TouchableOpacity className="bg-red-600 rounded-full py-3 items-center">
            <Text className="text-white font-semibold">Terminate Session</Text>
          </TouchableOpacity>
        </Animated.View>
      ) : null}
    </SafeAreaView>
  );
}