import { Stack } from "expo-router";
import "./globals.css";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="splash" options={{title:"Museum Navigator"}} />
      {/* <Stack.Screen name="role-selection" options={{title:"Choose your role"}}/> */}
    </Stack>
  )
}
