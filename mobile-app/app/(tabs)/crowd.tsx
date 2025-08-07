import React, { JSX, useEffect, useState } from 'react';
import { View, Text, Image, Dimensions, TouchableOpacity, SafeAreaView } from 'react-native';
import Svg, { Defs, RadialGradient, Stop, Circle } from 'react-native-svg';
import Header from '@/components/Header';
import { jetsonIdAtom, mapDataAtom, mapIdAtom } from '../state/globalState';
import { useAtom } from 'jotai';
import axios from 'axios';

const mapImages: Record<'map_01' | 'map_02' | 'map_03', any> = {
  "map_01": require('@/assets/images/map_01.png'),
  "map_02": require('@/assets/images/map_01.png'),
  "map_03": require('@/assets/images/map_01.png'),
};

export default function CrowdHeatmapScreen() {
  const [densityGrid, setDensityGrid] = useState({});
  const [jetsonId, setJetsonId] = useAtom(jetsonIdAtom);
  const [mapId,] = useAtom(mapIdAtom);
  const [mapData,] = useAtom(mapDataAtom);

  const fallbackMapId = "map_01";
  const selectedMapId = mapId || fallbackMapId;
  const mapImage = mapImages[selectedMapId as keyof typeof mapImages] || mapImages[fallbackMapId];

  const screenWidth = Dimensions.get('window').width;

  const mapOriginalWidth = mapData?.["map_width_in_px"] ?? 296;  // 296 pixels as fallback
  const mapOriginalHeight = mapData?.["map_height_in_px"] ?? 448; // 448 pixels
  const aspectRatio = mapOriginalWidth / mapOriginalHeight;

  const imageWidth = screenWidth;
  const imageHeight = screenWidth / aspectRatio;

  const tileWidth = mapData?.["tile_width"] ?? 8;  // same as backend tile_dimensions[0]
  const tileHeight = mapData?.["tile_height"] ?? 8; // same as backend tile_dimensions[1]

  const fetchDensityData = async () => {
    try {
      const uri = `http://10.0.2.2:8000/crowd-heatmap/${jetsonId}`
      const response = await axios.get(uri);
      const density_grid = response.data.density_grid;
      setDensityGrid(density_grid);
    } catch (error) {
      console.error('Failed to fetch crowd density:', error);
    }
  };

  const renderHeatmapCircles = () => {
    const circles: JSX.Element[] = [];

    Object.entries(densityGrid).forEach(([key, density], index) => {
      const [gridX, gridY] = key.replace('(', '').replace(')', '').split(',').map(Number);
      const centerX = (gridX * tileWidth + tileWidth / 2) * (imageWidth / mapOriginalWidth);
      const centerY = (gridY * tileHeight + tileHeight / 2) * (imageHeight / mapOriginalHeight);

      const radius = 20;  // You can adjust this based on desired heat spot size

      circles.push(
        <Circle
            key={`heat-${index}`}
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="url(#grad)"
            opacity={Number(density)}
        />
    );

    });

    return circles;
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: 'white' }}>
      <Header headerName="Crowd Heatmap" />
      <View className='flex-1 justify-center items-center'>
        <View style={{ width: imageWidth, height: imageHeight, position: 'relative' }}>
          <Image
            source={mapImage}
            className='w-full h-full'
            style={{
              resizeMode: 'contain',
            }}
          />

          <Svg
            width={imageWidth}
            height={imageHeight}
            style={{ position: 'absolute', top: 0, left: 0 }}
          >
            <Defs>
              <RadialGradient id="grad" cx="50%" cy="50%" rx="50%" ry="50%">
                <Stop offset="0%" stopColor="red" stopOpacity="1" />
                <Stop offset="50%" stopColor="orange" stopOpacity="0.7" />
                <Stop offset="100%" stopColor="blue" stopOpacity="0" />
              </RadialGradient>
            </Defs>
            {renderHeatmapCircles()}
          </Svg>
        </View>

        <TouchableOpacity
          onPress={fetchDensityData}
          className='w-4/5 py-3 bg-green-600 rounded-lg mt-5 items-center'
        >
          <Text className='text-white text-xl font-semibold'>Fetch Crowd Heatmap</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
