import { Stack } from "expo-router";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { View } from "react-native";
import UserInterviewScreen from './UserInterview';
import Dashboard from './Dashboard';

function RootLayoutNav() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <View />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      {user ? (
        <>
          <Stack.Screen name="(app)" />
          <Stack.Screen name="UserInterview" component={UserInterviewScreen} />
          <Stack.Screen name="Dashboard" component={Dashboard} />
        </>
      ) : (
        <Stack.Screen name="auth" />
      )}
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootLayoutNav />
    </AuthProvider>
  );
}