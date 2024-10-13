import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Dimensions,
  Image,
  Alert,
  Animated,
} from 'react-native';
import { getAuth, signOut } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import {
  getFirestore,
  collection,
  query,
  orderBy,
  doc,
  getDoc,
  onSnapshot,
} from 'firebase/firestore';
import { LinearGradient } from 'expo-linear-gradient';

const { width } = Dimensions.get('window');
const maxWidth = width - 40;

const slides = [
  {
    image: require('../assets/los-angeles.jpg'),
    message: 'Exploring the vibrant city of Los Angeles',
  },
  {
    image: require('../assets/hollywood.jpg'),
    message: 'Walking among the stars at Hollywood Boulevard',
  },
  {
    image: require('../assets/beach.jpg'),
    message: 'Relaxing at the sunny Venice Beach',
  },
];

const Dashboard = () => {
  const [userId, setUserId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [participantNames, setParticipantNames] = useState({});
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true); // Track loading state
  const progress = useRef(new Animated.Value(0)).current;
  const db = getFirestore();
  const router = useRouter();
  let refreshInterval = useRef(null);

  useEffect(() => {
    const fetchUserId = async () => {
      try {
        const storedUserId = await AsyncStorage.getItem('userId');
        setUserId(storedUserId);

        if (storedUserId) {
          const userDocRef = doc(db, 'users1', storedUserId);
          const userDoc = await getDoc(userDocRef);

          if (userDoc.exists()) {
            const userData = userDoc.data();
            if (!userData.UserID) {
              router.replace('/UserInterview');
              return;
            } else {
              subscribeToConversations(storedUserId);
              initiateSimulationWithRefresh(storedUserId);
            }
          } else {
            router.replace('/auth/welcome');
          }
        } else {
          router.replace('/auth/welcome');
        }
      } catch (error) {
        console.error('Error fetching user data:', error);
      }
    };

    fetchUserId();
    return () => clearInterval(refreshInterval.current); // Cleanup on unmount
  }, []);

  useEffect(() => {
    if (isLoading) {
      startProgress(); // Start the progress when loading
    }
  }, [isLoading]);

  useEffect(() => {
    let timer;
    if (conversations.length === 0) {
      timer = setInterval(() => {
        setCurrentSlideIndex((prevIndex) => (prevIndex + 1) % slides.length);
      }, 3000); // Change slide every 3 seconds
    }
    return () => clearInterval(timer);
  }, [conversations.length]);

  const initiateSimulationWithRefresh = (uid) => {
    console.log('Initiating simulation with refresh for user:', uid);
  
    refreshInterval.current = setInterval(() => {
      console.log('Triggering matching simulation from interval...');
      runMatchingSimulation(uid);
    }, 10000); // Refresh every 10 seconds
  
    // Run the first simulation immediately
    runMatchingSimulation(uid);
  };
  
  const runMatchingSimulation = async (uid) => {
    console.log('Starting matching simulation for user:', uid);
  
    try {
      const response = await fetch(
        `http://localhost:8000/run_matching_simulation?user_id=${uid}`,
        { method: 'POST' }
      );
  
      if (!response.ok) {
        console.error('Simulation request failed.');
        Alert.alert('Error', 'Failed to run simulation. Please try again.');
        setIsLoading(false);
        clearInterval(refreshInterval.current);
        return;
      }
  
      console.log('Simulation request sent. Starting continuous match check...');
      startContinuousMatchCheck(uid); // Ensure this is called correctly.
    } catch (error) {
      console.error('Error during simulation initiation:', error);
      setIsLoading(false);
    }
  };
  
  const startContinuousMatchCheck = (uid) => {
    console.log('Starting continuous match check for user:', uid);
  
    const q = query(
      collection(db, `users1/${uid}/conversations`),
      orderBy('compatibility', 'desc')
    );
  
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        console.log('Received snapshot from Firestore.');
  
        const data = snapshot.docs
          .map((doc) => ({ id: doc.id, ...doc.data() }))
          .filter((conversation) => conversation.compatibility != null);
  
        setConversations(data);
  
        if (data.length > 0) {
          console.log(`Found ${data.length} match(es).`);
          data.forEach((match, index) => {
            console.log(`Match ${index + 1}:`, match);
          });
  
          setIsLoading(false);
          console.log('Stopping match check as matches are found.');
          unsubscribe(); // Stop listening for changes once matches are found.
        } else {
          console.log('No matches yet. Waiting for updates...');
        }
      },
      (error) => {
        console.error('Error receiving Firestore updates:', error);
      }
    );
  };  

  const startProgress = () => {
    Animated.timing(progress, {
      toValue: 1000,
      duration: 500000, // 15 minutes in milliseconds
      useNativeDriver: false,
    }).start();
  };

  const subscribeToConversations = (uid) => {
    const q = query(
      collection(db, `users1/${uid}/conversations`),
      orderBy('compatibility', 'desc')
    );
  
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const data = snapshot.docs
        .map((doc) => ({ id: doc.id, ...doc.data() }))
        .filter((conversation) => conversation.compatibility != null);
  
      setConversations(data);
  
      data.forEach((conversation) => {
        const otherUserId = conversation.users.find((id) => id !== uid);
        if (otherUserId) {
          // Ensure the fake name is set immediately
          setParticipantNames((prevNames) => ({
            ...prevNames,
            [otherUserId]: prevNames[otherUserId] || generateRandomName(),
          }));
          // Try fetching the real name, which will overwrite the fake one if successful
          fetchParticipantName(otherUserId);
        }
      });
    });
  
    return unsubscribe;
  };  

  const fetchParticipantName = async (uid) => {
    try {
      const basicInfoRef = doc(db, `users1/${uid}/UsersID`, 'BasicInfo');
      const basicInfoDoc = await getDoc(basicInfoRef);
  
      if (basicInfoDoc.exists()) {
        const basicInfoData = basicInfoDoc.data();
        const name = basicInfoData?.Name || generateRandomName();
  
        // Ensure state updates correctly with a new object reference
        setParticipantNames((prevNames) => ({
          ...prevNames,
          [uid]: name,
        }));
      } else {
        console.warn(`No BasicInfo found for user: ${uid}`);
      }
    } catch (error) {
      console.error('Error fetching participant name:', error);
    }
  };
  
  const generateRandomName = () => {
    const names = ['Kim', 'Jane', 'Jill', 'Kerry', 'Jenny'];
    return names[Math.floor(Math.random() * names.length)];
  };

  const navigateToSummary = (conversation) => {
    const summary = conversation.analysis?.summary || 'No summary available';
    router.push({
      pathname: '/summary',
      params: { summary },
    });
  };

    const fallbackNames = ['Jenny', 'Kim', 'Jane', 'Kerry', 'Jill'];

    const getFallbackName = (index) => {
    return fallbackNames[index % fallbackNames.length]; // Rotate names based on the index
    };


  const handleSignOut = async () => {
    try {
      const auth = getAuth();
      await signOut(auth);
      await AsyncStorage.removeItem('userId');
      router.replace('/auth/welcome');
    } catch (error) {
      console.error('Sign out error:', error);
    }
  };

  return (
    <LinearGradient
      colors={['#FF416C', '#FF4B2B']}
      style={styles.gradient}
      start={[0, 0]}
      end={[1, 1]}
    >
      <View style={styles.container}>
        <TouchableOpacity style={styles.button} onPress={handleSignOut}>
          <Text style={styles.buttonText}>Sign Out</Text>
        </TouchableOpacity>

        {isLoading ? (
          <View style={styles.noConversationsContainer}>
            <Text style={styles.subHeaderText}>Simulating 1000+ dates...</Text>
            <Text style={styles.headerText}>
              {slides[currentSlideIndex].message}
            </Text>
            <Image
              source={slides[currentSlideIndex].image}
              style={styles.image}
              resizeMode="cover"
            />
            <View style={[styles.progressBarContainer, { width: maxWidth }]}>
              <Animated.View
                style={[
                  styles.progressBar,
                  {
                    width: progress.interpolate({
                      inputRange: [0, 1000],
                      outputRange: [0, maxWidth],
                    }),
                  },
                ]}
              />
            </View>
          </View>
        ) : (
          <>
            <Text style={styles.headerText}>
              Welcome! You have {conversations.length} date(s)
            </Text>
            <ScrollView contentContainerStyle={styles.stackView}>
                    {conversations.map((conversation, index) => (
                        <TouchableOpacity
                        key={conversation.id}
                        style={styles.conversationCard}
                        onPress={() => navigateToSummary(conversation)}
                        >
                        <Text style={styles.conversationTitle}>
                            {participantNames[conversation.users[0]] || getFallbackName(index)}
                        </Text>
                        <Text style={styles.text}>
                            Compatibility: {conversation.compatibility}
                        </Text>
                        </TouchableOpacity>
                    ))}
                    </ScrollView>
          </>
        )}
      </View>
    </LinearGradient>
  );
};

export default Dashboard;

const styles = StyleSheet.create({
  gradient: { flex: 1 },
  container: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 50,
  },
  progressBarContainer: {
    height: 20,
    width: '100%',
    backgroundColor: '#fff',
    borderRadius: 20,
    marginTop: 20,
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#000',
    borderRadius: 200,
  },
  subHeaderText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 5,
    textAlign: 'center',
  },
  headerText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#fff',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 25,
    marginVertical: 10,
  },
  buttonText: { color: '#FF416C', fontSize: 18, fontWeight: 'bold' },
  stackView: { alignItems: 'center', width: '100%', paddingVertical: 10 },
  conversationCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    padding: 15,
    marginVertical: 10,
    borderRadius: 15,
    width: width - 40,
  },
  conversationTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#FF4B2B',
  },
  text: { fontSize: 16, color: '#333', marginBottom: 5 },
  noConversationsContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 50,
  },
  image: {
    width: width - 40,
    height: 300,
    borderRadius: 15,
    marginTop: 20,
  },
  spinner: {
    marginTop: 20,
  },
});