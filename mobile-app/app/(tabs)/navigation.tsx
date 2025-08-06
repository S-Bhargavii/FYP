import { View, Text, SafeAreaView, Dimensions, Animated, Easing, TouchableOpacity } from 'react-native'
import { Picker } from '@react-native-picker/picker';
import React, { useEffect, useMemo, useRef, useState } from 'react'
import Header from '@/components/Header'
import { useAtom } from 'jotai'
import { jetsonIdAtom, poseAtom } from '../state/globalState'
import axios from 'axios'
import Svg, { Polyline, Circle } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';

const navigation = () => {
  const [position] = useAtom(poseAtom);
  const [jetsonId] = useAtom(jetsonIdAtom);

  // hard code for now 
  const [destinations] = useState([
      "Join or Die : An Americal Army Takes Shape Boston, 1775",
      "King George's Statue",
      "Chain Of States",
      "Independence Theatre",
      "The War Begins, 1775",
      "Boston's Liberty Tree",
      "Prologue: Tearing Down The King",
      "The Price Of Victory"
    ]);

  const [routeTypes, setRouteTypes] = useState(["fast", "less-crowd"]);

  // get user's preference
  const [selectedDestination, setSelectedDestination] = useState("The Price Of Victory");
  const [selectedRouteType, setSelectedRouteType] = useState("fast");
  
  const [pathPoints, setPathPoints] = useState([]);
  const [hasDeviated, setHasDeviated] = useState(false);

  const mapImage = require('@/assets/images/map_01.png');
  const screenWidth = Dimensions.get('window').width;
  const mapOriginalWidth = 296;
  const mapOriginalHeight = 448;
  const aspectRatio = mapOriginalWidth / mapOriginalHeight; 

  const imageWidth = screenWidth;
  const imageHeight = screenWidth / aspectRatio;

  const markerSize = 10;
  const markerPosition = useRef(new Animated.ValueXY({x:0, y:0})).current;

  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const panelAnim = useRef(new Animated.Value(0)).current; // 0-> open 1-> closed
  
    // side effect to changing user live position
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

  // side effect to panel
  useEffect(() => {
      Animated.timing(panelAnim, {
        toValue: isPanelOpen ? 0 : 1,
        duration: 300,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      }).start();
    }, [isPanelOpen]);
  
  const fetchPath = async() => {
    try{
      // setSelectedDestination("The Price Of Victory");
      // setSelectedRouteType("fast");
      const encodedDestination = encodeURIComponent(selectedDestination);

      const response = await axios.get(`http://10.0.2.2:8000/route/${selectedRouteType}/${encodedDestination}/${jetsonId}`);
      const path = response.data.path;
      console.log("Setting path points")
      setPathPoints(path);
      console.log(pathPoints)
    } catch(err){
      console.error("Failed to fetch path : ", err);
    }
  }

  const checkDeviation = () => {
    // calculate the nearest distance to the route
    const nearestDist = Math.min(...pathPoints.map(p => Math.sqrt(Math.pow(p[0]- position.x,2) + Math.pow(p[1] - position.y,2))))
    if (nearestDist > 20){
      // then user has deviated from the path 
      console.log("User deviated from path");
      setHasDeviated(true);
    }
  }
  
  const handleReroute = () => {
    fetchPath();
    setHasDeviated(false);
  };

  useEffect(() => {
    // useEffect is used for the logic to be executed without 
    // rerendering the component
    checkDeviation();
  }, [position.x, position.y]);

  const transformedPathPoints = useMemo(() => {
    console.log("Transforming ALL pathPoints once");
    return pathPoints.map((point) => {
        if (!point || typeof point[0] !== 'number' || typeof point[1] !== 'number') {
        return { x: 0, y: 0 };
        }
        return {
        x: (point[0] / mapOriginalWidth) * imageWidth,
        y: (point[1] / mapOriginalHeight) * imageHeight
        };
    });
    }, [pathPoints, imageWidth, imageHeight]);  // Dependency array

    const panelTranslateY = panelAnim.interpolate({
        inputRange: [0, 1],
        outputRange: [0, 200]  // Adjust 200px depending on how high you want it to collapse
    });

 return (
    <SafeAreaView style={{ flex: 1, backgroundColor: 'white' }}>
      <View className="w-full items-center justify-center py-4 bg-[#98733c]">
                <Text className="text-xl font-bold text-white">Navigation</Text>
          </View>

      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <View style={{ width: imageWidth, height: imageHeight, position: 'relative' }}>
          {/* Map Image */}
          <Animated.Image
            source={mapImage}
            style={{
              width: imageWidth,
              height: imageHeight,
              position: 'absolute',
              top: 0,
              left: 0,
              resizeMode: 'contain',
              zIndex: 0,
            }}
          />
            
        {/* Reroute Button (Top Right) */}
        {hasDeviated && (
        <TouchableOpacity
            style={{
            position: 'absolute',
            top: 10,
            right: 10,
            backgroundColor: 'red',
            paddingVertical: 8,
            paddingHorizontal: 12,
            borderRadius: 8,
            zIndex: 10
            }}
            onPress={handleReroute}  // Handle reroute logic here
        >
            <Text style={{ color: 'white', fontWeight: 'bold' }}>Reroute</Text>
        </TouchableOpacity>
        )}
          {/* path overlay */}
          <Svg width={imageWidth} height={imageHeight} style={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }}>
            {transformedPathPoints.map((p, idx) => (
                <Circle
                key={idx}
                cx={p.x}
                cy={p.y}
                r={4}
                fill="blue"
                />
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
          
        {/* Bottom Slide-Up Panel */}
      <Animated.View style={{
        position: 'absolute',
        bottom: 0,
        width: '100%',
        backgroundColor: 'white',
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        elevation: 10,
        padding: 16,
        transform: [{ translateY: panelTranslateY }]
      }}>
        {/* Expand/Collapse Arrow */}
        <TouchableOpacity
          style={{ alignItems: 'center', marginBottom: 10 }}
          onPress={() => setIsPanelOpen(!isPanelOpen)}
        >
          <Ionicons name={isPanelOpen ? "chevron-down" : "chevron-up"} size={24} color="black" />
        </TouchableOpacity>

        {isPanelOpen && (
          <>
            <Text style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 8 }}>Destination:</Text>
            <Picker selectedValue={selectedDestination} onValueChange={setSelectedDestination}>
              {destinations.map((dest, idx) => (
                <Picker.Item key={idx} label={dest} value={dest} />
              ))}
            </Picker>

            <Text style={{ fontSize: 16, fontWeight: 'bold', marginTop: 16, marginBottom: 8 }}>Route Type:</Text>
            <Picker selectedValue={selectedRouteType} onValueChange={setSelectedRouteType}>
              <Picker.Item label="Fastest Route" value="fast" />
              <Picker.Item label="Less Crowded" value="less-crowd" />
            </Picker>

            <TouchableOpacity
              style={{ marginTop: 16, backgroundColor: 'blue', padding: 12, borderRadius: 8 }}
              onPress={fetchPath}
            >
              <Text style={{ color: 'white', textAlign: 'center' }}>Start Navigation</Text>
            </TouchableOpacity>
          </>
        )}
      </Animated.View>
    </SafeAreaView>
  );
};

export default navigation