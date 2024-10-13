// welcome.tsx
import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  TouchableOpacity,
  View,
  TextInput,
  KeyboardAvoidingView,
  ScrollView,
  Platform,
  Animated,
  Easing,
  SafeAreaView,
} from 'react-native';
import { ThemedText } from '@/components/ThemedText';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  User,
} from 'firebase/auth';
import { app } from '@/config/firebaseConfig';
import { getFirestore, doc, setDoc, getDoc } from 'firebase/firestore';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';

const auth = getAuth(app);
const db = getFirestore(app);

export default function WelcomeScreen({ navigation }: NativeStackScreenProps<any>) {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const fadeAnim = useState(new Animated.Value(0))[0];

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    AsyncStorage.getItem('userId').then((uid) => {
      console.log(`[Debug] Retrieved userId from AsyncStorage: ${uid}`);
    });
  }, []);

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 1500,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  React.useLayoutEffect(() => {
    if (navigation) {
      navigation.setOptions({
        headerShown: false,
      });
    }
  }, [navigation]);

  const handleAuth = async () => {
    try {
      let userCredential;
      if (isSignUp) {
        userCredential = await createUserWithEmailAndPassword(auth, email, password);
        setSuccessMessage('Sign up successful!');

        const { uid, email: userEmail } = userCredential.user;
        console.log(`[Auth] User signed up: ${uid}`);

        await setDoc(doc(db, 'users1', uid), { email: userEmail, uid });
      } else {
        userCredential = await signInWithEmailAndPassword(auth, email, password);
        setSuccessMessage('Sign in successful!');
        console.log(`[Auth] User signed in: ${userCredential.user.uid}`);
      }

      const { uid } = userCredential.user;

      await AsyncStorage.setItem('userId', uid);
      console.log(`[Auth] Stored UID in AsyncStorage: ${uid}`);

      const userDoc = await getDoc(doc(db, 'users1', uid));
      console.log(`[Firestore] User doc fetched: ${JSON.stringify(userDoc.data())}`);

      if (userDoc.exists() && userDoc.data().UserID) {
        console.log(`[Navigation] Navigating to Dashboard`);
        router.replace('/Dashboard');
      } else {
        console.log(`[Navigation] Navigating to UserInterview`);
        router.replace('/UserInterview');
      }

      setEmail('');
      setPassword('');
      setError('');
    } catch (error) {
      console.error(`[Error] ${error.message}`);
      setError(error.message);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut(auth);
      await AsyncStorage.removeItem('userId');
      setUser(null);
      router.replace('/auth/welcome');
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={80}
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1 }}>
        <LinearGradient
          colors={['#FF416C', '#FF4B2B']}
          style={styles.gradient}
          start={[0, 0]}
          end={[1, 1]}
        >
          <SafeAreaView style={{ flex: 1 }}>
            <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
              <View style={styles.content}>
              <ThemedText
                  type="title"
                  style={styles.title}
                  adjustsFontSizeToFit
                  numberOfLines={1}
                >
                  Welcome to Serendipidates
                </ThemedText>
                <ThemedText
                  style={styles.description}
                  adjustsFontSizeToFit
                  numberOfLines={1}
                >
                  Let AI go on dates for you
                </ThemedText>
                {user ? (
                  <View style={styles.userContainer}>
                    <ThemedText
                     
                    style={styles.loggedInMessage}>
                      Welcome: You are logged in as {user.email}
                    </ThemedText>
                    <TouchableOpacity style={styles.button} onPress={handleSignOut}>
                      <ThemedText style={styles.buttonText}>Sign Out</ThemedText>
                    </TouchableOpacity>
                  </View>
                ) : successMessage ? (
                  <View style={styles.successContainer}>
                    <ThemedText style={styles.successMessage}>{successMessage}</ThemedText>
                  </View>
                ) : (
                  <View style={styles.authContainer}>
                    <TextInput
                      style={styles.input}
                      placeholder="Email"
                      placeholderTextColor="#fff"
                      value={email}
                      onChangeText={setEmail}
                      keyboardType="email-address"
                      autoCapitalize="none"
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Password"
                      placeholderTextColor="#fff"
                      value={password}
                      onChangeText={setPassword}
                      secureTextEntry
                    />
                    {error ? <ThemedText style={styles.errorText}>{error}</ThemedText> : null}
                    <TouchableOpacity style={styles.button} onPress={handleAuth}>
                      <ThemedText style={styles.buttonText}>
                        {isSignUp ? 'Sign Up' : 'Sign In'}
                      </ThemedText>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => setIsSignUp(!isSignUp)}>
                      <ThemedText style={styles.switchText}>
                        {isSignUp
                          ? 'Already have an account? Sign In'
                          : "Don't have an account? Sign Up"}
                      </ThemedText>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            </Animated.View>
          </SafeAreaView>
        </LinearGradient>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  container: {
    flex: 1,
    // Removed padding to prevent content shifting
  },
  content: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 48,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#fff',
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  description: {
    fontSize: 22,
    textAlign: 'center',
    marginBottom: 30,
    paddingHorizontal: 20,
    color: '#fff',
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 5,
    flexShrink: 1,
  },
  userContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  loggedInMessage: {
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
    color: '#fff',
  },
  authContainer: {
    width: '100%',
    alignItems: 'center',
  },
  input: {
    width: '100%',
    height: 50,
    borderColor: '#fff',
    borderWidth: 1,
    borderRadius: 25,
    marginBottom: 15,
    paddingHorizontal: 20,
    color: '#fff',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  button: {
    backgroundColor: '#fff',
    width: '60%',
    paddingVertical: 15,
    borderRadius: 25,
    marginTop: 10,
    alignItems: 'center',
  },
  buttonText: {
    color: '#FF416C',
    fontWeight: 'bold',
    fontSize: 18,
  },
  switchText: {
    marginTop: 15,
    color: '#fff',
    fontWeight: 'bold',
  },
  errorText: {
    color: 'yellow',
    marginBottom: 10,
  },
});