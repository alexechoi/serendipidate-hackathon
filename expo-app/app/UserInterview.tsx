import React, { useEffect, useState, useRef } from 'react';
import {
  SafeAreaView,
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Text,
} from 'react-native';
import { getAuth } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { getFirestore, doc, getDoc } from 'firebase/firestore';
import { LinearGradient } from 'expo-linear-gradient';

const API_URL = 'http://127.0.0.1:8000';

const UserInterview = () => {
  const [userId, setUserId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState('');
  const [isInterviewComplete, setIsInterviewComplete] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const flatListRef = useRef<FlatList<any>>(null);

  const db = getFirestore();

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
            if (userData.UserID) {
              router.replace('/Dashboard');
              return;
            } else {
              startInterview(storedUserId);
            }
          } else {
            router.replace('/auth/welcome');
            return;
          }
        } else {
          router.replace('/auth/welcome');
        }
      } catch (error) {
        console.error('Error fetching user data:', error);
        setErrorMessage('Error fetching user data.');
      }
    };

    fetchUserId();
  }, []);

  useEffect(() => {
    // Scroll to the bottom whenever messages change
    if (flatListRef.current) {
      flatListRef.current.scrollToEnd({ animated: true });
    }
  }, [messages]);

  const startInterview = async (uid: string) => {
    try {
      setIsWaitingForResponse(true);
      const url = `${API_URL}/start_interview?user_id=${uid}`;
      console.log('Calling API:', url);
      const response = await fetch(url, { method: 'POST' });
      const data = await response.json();
      addMessage(data.initial_question, 'ai');
      setIsWaitingForResponse(false);
    } catch (error) {
      console.error('Error starting interview:', error);
      setErrorMessage('Failed to start the interview. Please try again.');
      setIsWaitingForResponse(false);
    }
  };

  const submitAnswer = async (answer: string) => {
    try {
      addMessage(answer, 'user');
      setIsWaitingForResponse(true);

      const response = await fetch(`${API_URL}/submit_answer?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: answer }),
      });
      const data = await response.json();

      if (data.message === 'Interview completed') {
        setIsInterviewComplete(true);
        addMessage('Interview completed. Thank you for your time!', 'ai');
        generateProfile();
      } else if (data.next_question) {
        addMessage(data.next_question, 'ai');
      }

      setIsWaitingForResponse(false);
    } catch (error) {
      console.error('Error submitting answer:', error);
      setErrorMessage('Error submitting your answer.');
      setIsWaitingForResponse(false);
    }
  };

  const generateProfile = async () => {
    try {
      const response = await fetch(`${API_URL}/generate_profile?user_id=${userId}`);
      const data = await response.json();
      console.log('Generated profile:', data.profile);
      router.replace('/Dashboard');
    } catch (error) {
      console.error('Error generating profile:', error);
      setErrorMessage('Error generating your profile.');
    }
  };

  const addMessage = (content: string, sender: 'user' | 'ai') => {
    setMessages((prevMessages) => [
      ...prevMessages,
      { id: Date.now().toString(), text: content, sender },
    ]);
    setErrorMessage(null);
  };

  const handleSend = () => {
    if (inputText.trim() && !isInterviewComplete && !isWaitingForResponse) {
      submitAnswer(inputText.trim());
      setInputText('');
    }
  };

  const renderMessage = ({ item }: { item: any }) => (
    <View
      style={[
        styles.messageBubble,
        item.sender === 'user' ? styles.userBubble : styles.aiBubble,
      ]}
    >
      <Text style={styles.messageText}>{item.text}</Text>
    </View>
  );

  const shouldDisableInput = isInterviewComplete || isWaitingForResponse;

  return (
    <LinearGradient
      colors={['#FF416C', '#FF4B2B']}
      style={styles.gradient}
      start={[0, 0]}
      end={[1, 1]}
    >
      <SafeAreaView style={styles.container}>
        {errorMessage && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: true })
          }
        />

        {!isInterviewComplete && (
          <View style={styles.inputContainer}>
            <TextInput
              style={[
                styles.input,
                shouldDisableInput && { backgroundColor: 'gray' },
              ]}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Type your answer..."
              placeholderTextColor="#fff"
              onSubmitEditing={handleSend}
              editable={!shouldDisableInput}
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={handleSend}
              disabled={shouldDisableInput}
            >
              <Text style={styles.sendButtonText}>Send</Text>
            </TouchableOpacity>
          </View>
        )}
      </SafeAreaView>
    </LinearGradient>
  );
};

export default UserInterview;

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  container: {
    flex: 1,
    padding: 20,
  },
  errorContainer: {
    padding: 10,
    backgroundColor: 'rgba(255, 0, 0, 0.1)',
    borderRadius: 10,
    marginBottom: 10,
  },
  errorText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
  },
  messageList: {
    flexGrow: 1,
    justifyContent: 'flex-end',
    paddingHorizontal: 10,
  },
  messageBubble: {
    padding: 15,
    borderRadius: 20,
    marginVertical: 5,
    maxWidth: '75%',
    elevation: 2,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#FF6F61',
    marginRight: 10,
  },
  aiBubble: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    marginLeft: 10,
  },
  messageText: {
    color: '#000',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.5)',
    paddingVertical: 10,
    paddingHorizontal: 15,
    backgroundColor: 'rgba(255, 75, 43, 0.9)',
  },
  input: {
    flex: 1,
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    color: '#fff',
    marginRight: 10,
  },
  sendButton: {
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  sendButtonText: {
    color: '#FF416C',
    fontWeight: 'bold',
  },
});