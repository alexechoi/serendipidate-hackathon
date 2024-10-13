import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyD5r4AnvY-K56_uK9fArJEJv6QCQWeCyZI",
  authDomain: "connection-ai-ae016.firebaseapp.com",
  projectId: "connection-ai-ae016",
  storageBucket: "connection-ai-ae016.appspot.com",
  messagingSenderId: "627416190443",
  appId: "1:627416190443:web:fbac0af41f5301533cddae"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db = getFirestore(app);