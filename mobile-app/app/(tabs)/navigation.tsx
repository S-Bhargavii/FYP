import { View, Text, SafeAreaView } from 'react-native'
import React from 'react'
import Header from '@/components/Header'

const navigation = () => {
  return (
        <SafeAreaView className="flex-1 bg-white dark:bg-black">
          <Header headerName='Navigation'/>
        </SafeAreaView>
  )
}

export default navigation