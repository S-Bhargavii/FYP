import React, { JSX, useEffect, useState } from 'react';
import { View, Text, Image, Dimensions, TouchableOpacity, SafeAreaView } from 'react-native';
import Svg, { Defs, RadialGradient, Stop, Circle } from 'react-native-svg';
import Header from '@/components/Header';
import { jetsonIdAtom } from '../state/globalState';
import { useAtom } from 'jotai';
import axios from 'axios';

export default function CrowdHeatmapScreen() {
  const [densityGrid, setDensityGrid] = useState({});
  const [jetsonId, setJetsonId] = useAtom(jetsonIdAtom);
  
  const mapImage = require('@/assets/images/map_01.png');

  const screenWidth = Dimensions.get('window').width;
  const screenHeight = Dimensions.get('window').height;

  const mapOriginalWidth = 37 * 8;  // 296 pixels
  const mapOriginalHeight = 56 * 8; // 448 pixels
  const aspectRatio = mapOriginalWidth / mapOriginalHeight;

  const imageWidth = screenWidth;
  const imageHeight = screenWidth / aspectRatio;

  const tileWidth = 8;  // same as backend tile_dimensions[0]
  const tileHeight = 8; // same as backend tile_dimensions[1]

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

      const radius = 60;  // You can adjust this based on desired heat spot size

      circles.push(
        <Circle
            key={`heat-${index}`}
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="url(#grad)"
            opacity={Number(density)}  // <-- Explicit casting to number
        />
    );

    });

    return circles;
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: 'white' }}>
      <Header headerName="Crowd Heatmap" />
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <View style={{ width: imageWidth, height: imageHeight, position: 'relative' }}>
          <Image
            source={mapImage}
            style={{
              width: '100%',
              height: '100%',
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
          style={{
            width: '80%',
            padding: 15,
            backgroundColor: '#007bff',
            borderRadius: 8,
            marginTop: 20,
            alignItems: 'center',
          }}
        >
          <Text style={{ color: 'white', fontSize: 16 }}>Fetch Crowd Heatmap</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
