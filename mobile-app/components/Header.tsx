import { View, Text } from 'react-native'
import React from 'react'

type HeaderProps = {
  headerName: string;
};

const Header = ({ headerName }: HeaderProps) => {
  return (
    <View className="w-full items-center justify-center py-4 bg-[#98733c]">
          <Text className="text-xl font-bold text-white">{headerName}</Text>
    </View>
  )
}

export default Header