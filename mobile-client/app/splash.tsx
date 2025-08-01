// app/splash.tsx
import { View, Text, Image, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons'; // For the settings icon

export default function SplashScreen() {
  const router = useRouter();

  return (
    <View className="flex-1 bg-neutral-900 px-4 pt-12 pb-1200 justify-between">

      {/* Logo Card */}
      <View className="rounded-xl p-4 items-center justify-center">
        <Image
          source={require("../assets/images/splash_screen_logo.jpg")}
          className="w-128 h-80 rounded-xl"
          resizeMode="contain"
        />
      </View>

      {/* Bottom Title */}
      <Text
        className="text-white text-xl font-bold text-center"
        onPress={() => router.replace("/role-selection")}
      >
        Museum Navigator
      </Text>
    </View>
  );
}
