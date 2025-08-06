import { View, Text, SafeAreaView } from 'react-native'
import React from 'react'
import Header from '@/components/Header'

export default function crowd() {
  return (
        <SafeAreaView className="flex-1 bg-white dark:bg-black">
          <Header headerName='Crowd Check'/>
        </SafeAreaView>
  )
}