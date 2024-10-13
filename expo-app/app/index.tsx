import { Redirect } from "expo-router";
import { useAuth } from "@/hooks/useAuth";
import { LogBox } from 'react-native';
LogBox.ignoreLogs(['Warning: ...']); // Ignore log notification by message
LogBox.ignoreAllLogs();//Ignore all log notifications

export default function Index() {
  const { user } = useAuth();

  if (user) {
    return <Redirect href="/UserInterview" />;
  } else {
    return <Redirect href="/auth/welcome" />;
  }
}