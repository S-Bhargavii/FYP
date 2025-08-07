import React, { useEffect, useRef } from 'react';
import { View, Text, Dimensions, Animated, Easing, SafeAreaView } from 'react-native';
import { jetsonIdAtom, mapDataAtom, mapIdAtom, poseAtom } from '../state/globalState';
import { useAtom } from 'jotai';
import Header from '@/components/Header';

const mapImages: Record<'map_01' | 'map_02' | 'map_03', any> = {
  "map_01": require('@/assets/images/map_01.png'),
  "map_02": require('@/assets/images/map_01.png'),
  "map_03": require('@/assets/images/map_01.png'),
};

export default function LiveLocationScreen() {
  const [position] = useAtom(poseAtom);  // position = { x: ..., y: ... }

  const [mapId,] = useAtom(mapIdAtom);
  const [mapData,] = useAtom(mapDataAtom);

  const fallbackMapId = "map_01";
  const selectedMapId = mapId || fallbackMapId;
  const mapImage = mapImages[selectedMapId as keyof typeof mapImages] || mapImages[fallbackMapId];

  const screenWidth = Dimensions.get('window').width;

  const mapOriginalWidth = mapData?.["map_width_in_px"] ?? 296;  // 296 pixels as fallback
  const mapOriginalHeight = mapData?.["map_height_in_px"] ?? 448; // 448 pixels as fallback
  const aspectRatio = mapOriginalWidth / mapOriginalHeight;

  const imageWidth = screenWidth;
  const imageHeight = screenWidth / aspectRatio;

  const markerSize = 10;

  const markerPosition = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;

  useEffect(() => {
    const scaledX = (position.x / mapOriginalWidth) * imageWidth;
    const scaledY = (position.y / mapOriginalHeight) * imageHeight;
    Animated.timing(markerPosition, {
      toValue: { x: scaledX, y: scaledY },
      duration: 500, 
      useNativeDriver: true,
      easing: Easing.inOut(Easing.ease),
    }).start();
  }, [position.x, position.y]);

  return (

    <SafeAreaView className="flex-1 bg-white dark:bg-black">
      <Header headerName='Live Location'/>
      <View className='flex-1 justify-center items-center'>
        <View style={{ width: imageWidth, height: imageHeight, position: 'relative' }}>
          <Animated.Image
            source={mapImage}
            style={{
              width: '100%',
              height: '100%',
              resizeMode: 'contain',
            }}
          />

          <Animated.View
            style={{
              position: 'absolute',
              width: markerSize,
              height: markerSize,
              borderRadius: markerSize / 2,
              backgroundColor: 'red',
              transform: [
                { translateX: Animated.subtract(markerPosition.x, markerSize / 2) },
                { translateY: Animated.subtract(markerPosition.y, markerSize / 2) }
              ]
            }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}