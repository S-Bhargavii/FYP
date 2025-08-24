import { View, Text, SafeAreaView, Dimensions, Animated, Easing, TouchableOpacity } from 'react-native'
import { Picker } from '@react-native-picker/picker';
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useAtom } from 'jotai'
import { jetsonIdAtom, mapDataAtom, mapIdAtom, poseAtom } from '../state/globalState'
import axios from 'axios'
import Svg, { Circle } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';

const mapImages: Record<'map_01' | 'map_02' | 'map_03', any> = {
  "map_01": require('@/assets/images/map_01.png'),
  "map_02": require('@/assets/images/map_01.png'),
  "map_03": require('@/assets/images/map_01.png'),
};

const Navigation = () => {
  const [position] = useAtom(poseAtom);
  const [jetsonId] = useAtom(jetsonIdAtom);
  const [mapId,] = useAtom(mapIdAtom);
  const [mapData,] = useAtom(mapDataAtom);

  const destinations: { [key: string]: string } = mapData?.["landmarks_mapping"] ?? {};
  const destinationKeys = Object.keys(destinations);
  const [selectedDestination, setSelectedDestination] = useState(destinationKeys[0] ?? "");
  const [selectedRouteType, setSelectedRouteType] = useState("fast");
  const [pathPoints, setPathPoints] = useState([]);
  const [hasDeviated, setHasDeviated] = useState(false);

  const fallbackMapId = "map_01";
  const selectedMapId = mapId || fallbackMapId;
  const mapImage = mapImages[selectedMapId as keyof typeof mapImages] || mapImages[fallbackMapId];

  const screenWidth = Dimensions.get('window').width;
  const mapOriginalWidth = mapData?.["map_width_in_px"] ?? 296;  // 296 pixels as fallback
  const mapOriginalHeight = mapData?.["map_height_in_px"] ?? 448; // 448 pixels as fallback
  const aspectRatio = mapOriginalWidth / mapOriginalHeight;

  const imageWidth = screenWidth;
  const imageHeight = screenWidth / aspectRatio;

  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const panelAnim = useRef(new Animated.Value(0)).current;

  const togglePanel = (forceState?: boolean) => {
    const newState = forceState !== undefined ? forceState : !isPanelOpen;
    setIsPanelOpen(newState);
    Animated.timing(panelAnim, {
      toValue: newState ? 0 : 1,
      duration: 300,
      easing: Easing.inOut(Easing.ease),
      useNativeDriver: true,
    }).start();
  };

  useEffect(() => {
    const scaledX = (position.x / mapOriginalWidth) * imageWidth;
    const scaledY = (position.y / mapOriginalHeight) * imageHeight;

    Animated.timing(new Animated.ValueXY({ x: scaledX, y: scaledY }), {
      toValue: { x: scaledX, y: scaledY },
      duration: 500,
      useNativeDriver: true,
      easing: Easing.inOut(Easing.ease),
    }).start();
  }, [position.x, position.y]);

  const fetchPath = async () => {
    try {
      const encodedDestination = encodeURIComponent(selectedDestination);
      const encodedRouteType = encodeURIComponent(selectedRouteType);
      const encodedJetsonId = encodeURIComponent(jetsonId);
      const uri = `http://10.0.2.2:8000/route/${encodedRouteType}/${encodedDestination}/${encodedJetsonId}`;
      console.log(uri);
      const response = await axios.get(uri);
      const path = response.data.path;
      setPathPoints(path);
      togglePanel(false); // Collapse after navigation starts
    } catch (err) {
      console.error("Failed to fetch path: ", err);
    }
  };

  const checkDeviation = () => {
    const nearestDist = Math.min(...pathPoints.map(p => Math.sqrt(Math.pow(p[0] - position.x, 2) + Math.pow(p[1] - position.y, 2))));
    if (nearestDist > 20) {
      setHasDeviated(true);
    }
  };

  const handleReroute = () => {
    fetchPath();
    setHasDeviated(false);
  };

  useEffect(() => {
    checkDeviation();
  }, [position.x, position.y]);

  const transformedPathPoints = useMemo(() => {
    return pathPoints.map(point => {
      if (!point || typeof point[0] !== 'number' || typeof point[1] !== 'number') {
        return { x: 0, y: 0 };
      }
      return {
        x: (point[0] / mapOriginalWidth) * imageWidth,
        y: (point[1] / mapOriginalHeight) * imageHeight
      };
    });
  }, [pathPoints, imageWidth, imageHeight]);

  const panelTranslateY = panelAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 200]  // Adjust this value as needed
  });

  return (
    <SafeAreaView className="flex-1 bg-white">
      <View className="w-full items-center justify-center py-4 bg-[#98733c]">
        <Text className="text-xl font-bold text-white">Navigation</Text>
      </View>

      <View className="flex-1 items-center justify-center">
        <View style={{ width: imageWidth, height: imageHeight }} className="relative">
          <Animated.Image
            source={mapImage}
            className="absolute top-0 left-0 z-0"
            style={{ width: imageWidth, height: imageHeight, resizeMode: 'contain' }}
          />

          <Svg width={imageWidth} height={imageHeight} className="absolute top-0 left-0 z-10">
            {transformedPathPoints.map((p, idx) => (
              <Circle key={idx} cx={p.x} cy={p.y} r={2.5} fill="blue" />
            ))}
            {!isNaN(position.x) && !isNaN(position.y) && (
              <Circle
                cx={(position.x / mapOriginalWidth) * imageWidth}
                cy={(position.y / mapOriginalHeight) * imageHeight}
                r={5}
                fill="red"
              />
            )}
          </Svg>
        </View>
      </View>

      <View className='flex-row justify-between px-5'>
        {/* Floating Arrow Toggle Button */}
        <TouchableOpacity
          className="bottom-10 self-center bg-gray-200 p-2 rounded-full z-20"
          onPress={() => togglePanel()}
        >
          <Ionicons name={isPanelOpen ? "chevron-down" : "chevron-up"} size={24} color="black" />
        </TouchableOpacity>

        {/* Floating Reroute Button */}
        {hasDeviated && !isPanelOpen && (
          <TouchableOpacity
            className="bottom-10 self-center bg-red-600 py-3 px-7 rounded-full z-20"
            onPress={handleReroute}
          >
              <Text className="text-white text-xl font-semibold">Reroute</Text>
          </TouchableOpacity>
        )}
      </View>


      {/* Bottom Panel */}
      <Animated.View style={{ transform: [{ translateY: panelTranslateY }] }} className="absolute bottom-0 w-full bg-white rounded-t-2xl shadow-lg p-4">
        {isPanelOpen && (
          <>
            <Text className="text-base font-bold mb-2">Destination:</Text>
            <Picker selectedValue={selectedDestination} onValueChange={setSelectedDestination}>
              {destinationKeys.map((key, idx) => (
                <Picker.Item key={idx} label={key} value={key} />
              ))}
            </Picker>

            <Text className="text-base font-bold mt-4 mb-2">Route Type:</Text>
            <Picker selectedValue={selectedRouteType} onValueChange={setSelectedRouteType}>
              <Picker.Item label="Fastest Route" value="fast" />
              <Picker.Item label="Less Crowded" value="less-crowd" />
            </Picker>

            <TouchableOpacity className="mt-4 bg-green-600 py-3 rounded-lg" onPress={fetchPath}>
              <Text className="text-white text-xl text-center font-semibold">Start Navigation</Text>
            </TouchableOpacity>
          </>
        )}
      </Animated.View>
    </SafeAreaView>
  );
};

export default Navigation;
