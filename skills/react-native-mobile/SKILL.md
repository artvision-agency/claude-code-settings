---
name: react-native-mobile
description: React Native development patterns covering navigation, state management, camera, video, animations, native modules, and release builds
---

# React Native Mobile Development Patterns

## Overview

This skill covers practical patterns for building production React Native applications. It includes navigation setup, state management with Zustand, camera and video integration, animations with Reanimated, platform-specific code, native module bridges, testing, and release build configuration.

## React Navigation (Stack, Tabs, Drawer)

### Installation and Setup

```bash
npx expo install @react-navigation/native @react-navigation/native-stack \
  @react-navigation/bottom-tabs @react-navigation/drawer \
  react-native-screens react-native-safe-area-context \
  react-native-gesture-handler react-native-reanimated
```

### Type-Safe Navigation

```typescript
// src/navigation/types.ts
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type { CompositeScreenProps, NavigatorScreenParams } from "@react-navigation/native";

export type RootStackParamList = {
  Auth: undefined;
  MainTabs: NavigatorScreenParams<MainTabParamList>;
  VideoPlayer: { videoId: string; title: string };
  Camera: { mode: "photo" | "video" };
};

export type MainTabParamList = {
  Home: undefined;
  Search: { query?: string };
  Profile: { userId: string };
  Settings: undefined;
};

export type RootStackScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;

export type MainTabScreenProps<T extends keyof MainTabParamList> =
  CompositeScreenProps<
    BottomTabScreenProps<MainTabParamList, T>,
    NativeStackScreenProps<RootStackParamList>
  >;

// Enable type checking for useNavigation
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
```

### Navigator Components

```tsx
// src/navigation/RootNavigator.tsx
import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RootStackParamList } from "./types";
import { MainTabNavigator } from "./MainTabNavigator";
import { AuthScreen } from "../screens/AuthScreen";
import { VideoPlayerScreen } from "../screens/VideoPlayerScreen";
import { CameraScreen } from "../screens/CameraScreen";
import { useAuthStore } from "../stores/auth";

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator(): React.JSX.Element {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <>
            <Stack.Screen name="MainTabs" component={MainTabNavigator} />
            <Stack.Screen
              name="VideoPlayer"
              component={VideoPlayerScreen}
              options={{ presentation: "fullScreenModal", animation: "fade" }}
            />
            <Stack.Screen
              name="Camera"
              component={CameraScreen}
              options={{ presentation: "fullScreenModal" }}
            />
          </>
        ) : (
          <Stack.Screen name="Auth" component={AuthScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

```tsx
// src/navigation/MainTabNavigator.tsx
import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import Icon from "react-native-vector-icons/Ionicons";
import { MainTabParamList } from "./types";
import { HomeScreen } from "../screens/HomeScreen";
import { SearchScreen } from "../screens/SearchScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { SettingsScreen } from "../screens/SettingsScreen";

const Tab = createBottomTabNavigator<MainTabParamList>();

const TAB_ICONS: Record<keyof MainTabParamList, { focused: string; default: string }> = {
  Home: { focused: "home", default: "home-outline" },
  Search: { focused: "search", default: "search-outline" },
  Profile: { focused: "person", default: "person-outline" },
  Settings: { focused: "settings", default: "settings-outline" },
};

export function MainTabNavigator(): React.JSX.Element {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          const icons = TAB_ICONS[route.name];
          return (
            <Icon
              name={focused ? icons.focused : icons.default}
              size={size}
              color={color}
            />
          );
        },
        headerShown: false,
        tabBarActiveTintColor: "#007AFF",
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Search" component={SearchScreen} />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        initialParams={{ userId: "me" }}
      />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
```

## Zustand State Management

```typescript
// src/stores/auth.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";

interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl: string | null;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const response = await fetch("https://api.example.com/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
          const data = await response.json();
          set({
            user: data.user,
            token: data.token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch {
          set({ isLoading: false });
          throw new Error("Login failed");
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      setUser: (user) => set({ user }),
    }),
    {
      name: "auth-storage",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
```

```typescript
// src/stores/app.ts
import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

interface AppState {
  theme: "light" | "dark" | "system";
  language: string;
  notificationsEnabled: boolean;
  setTheme: (theme: "light" | "dark" | "system") => void;
  setLanguage: (language: string) => void;
  toggleNotifications: () => void;
}

export const useAppStore = create<AppState>()(
  subscribeWithSelector((set) => ({
    theme: "system",
    language: "en",
    notificationsEnabled: true,
    setTheme: (theme) => set({ theme }),
    setLanguage: (language) => set({ language }),
    toggleNotifications: () =>
      set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
  }))
);
```

## react-native-vision-camera Integration

```tsx
// src/screens/CameraScreen.tsx
import React, { useCallback, useRef, useState } from "react";
import { StyleSheet, View, TouchableOpacity, Text } from "react-native";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  PhotoFile,
  VideoFile,
  CameraPosition,
} from "react-native-vision-camera";
import { RootStackScreenProps } from "../navigation/types";

export function CameraScreen({ route, navigation }: RootStackScreenProps<"Camera">) {
  const { mode } = route.params;
  const cameraRef = useRef<Camera>(null);
  const [position, setPosition] = useState<CameraPosition>("back");
  const [isRecording, setIsRecording] = useState(false);
  const { hasPermission, requestPermission } = useCameraPermission();

  const device = useCameraDevice(position);

  const handleFlipCamera = useCallback(() => {
    setPosition((prev) => (prev === "back" ? "front" : "back"));
  }, []);

  const handleTakePhoto = useCallback(async () => {
    if (!cameraRef.current) return;
    const photo: PhotoFile = await cameraRef.current.takePhoto({
      flash: "auto",
      qualityPrioritization: "balanced",
    });
    navigation.goBack();
    // Process photo.path
  }, [navigation]);

  const handleStartRecording = useCallback(() => {
    if (!cameraRef.current) return;
    setIsRecording(true);
    cameraRef.current.startRecording({
      onRecordingFinished: (video: VideoFile) => {
        setIsRecording(false);
        navigation.goBack();
        // Process video.path
      },
      onRecordingError: (error) => {
        setIsRecording(false);
        console.error("Recording error:", error);
      },
    });
  }, [navigation]);

  const handleStopRecording = useCallback(() => {
    cameraRef.current?.stopRecording();
  }, []);

  if (!hasPermission) {
    return (
      <View style={styles.centered}>
        <Text>Camera permission is required</Text>
        <TouchableOpacity onPress={requestPermission}>
          <Text style={styles.link}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.centered}>
        <Text>No camera device available</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={true}
        photo={mode === "photo"}
        video={mode === "video"}
        audio={mode === "video"}
      />
      <View style={styles.controls}>
        <TouchableOpacity onPress={handleFlipCamera} style={styles.button}>
          <Text style={styles.buttonText}>Flip</Text>
        </TouchableOpacity>
        {mode === "photo" ? (
          <TouchableOpacity onPress={handleTakePhoto} style={styles.captureButton} />
        ) : (
          <TouchableOpacity
            onPress={isRecording ? handleStopRecording : handleStartRecording}
            style={[styles.captureButton, isRecording && styles.recording]}
          />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "black" },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  link: { color: "#007AFF", marginTop: 12, fontSize: 16 },
  controls: {
    position: "absolute",
    bottom: 40,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 32,
  },
  button: { padding: 12, backgroundColor: "rgba(255,255,255,0.3)", borderRadius: 8 },
  buttonText: { color: "white", fontWeight: "600" },
  captureButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "white",
    borderWidth: 4,
    borderColor: "rgba(255,255,255,0.5)",
  },
  recording: { backgroundColor: "red" },
});
```

## react-native-video Playback

```tsx
// src/components/VideoPlayer.tsx
import React, { useCallback, useRef, useState } from "react";
import { View, StyleSheet, TouchableOpacity, Text, ActivityIndicator } from "react-native";
import Video, { OnProgressData, OnLoadData, VideoRef } from "react-native-video";

interface VideoPlayerProps {
  uri: string;
  title: string;
}

export function VideoPlayer({ uri, title }: VideoPlayerProps) {
  const videoRef = useRef<VideoRef>(null);
  const [paused, setPaused] = useState(false);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const handleLoad = useCallback((data: OnLoadData) => {
    setLoading(false);
    setProgress((prev) => ({ ...prev, total: data.duration }));
  }, []);

  const handleProgress = useCallback((data: OnProgressData) => {
    setProgress({ current: data.currentTime, total: data.seekableDuration });
  }, []);

  const handleSeek = useCallback((seconds: number) => {
    videoRef.current?.seek(seconds);
  }, []);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <View style={styles.container}>
      <Video
        ref={videoRef}
        source={{ uri }}
        style={styles.video}
        resizeMode="contain"
        paused={paused}
        onLoad={handleLoad}
        onProgress={handleProgress}
        onError={(e) => console.error("Video error:", e)}
        repeat={false}
      />
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="white" />
        </View>
      )}
      <View style={styles.controls}>
        <TouchableOpacity onPress={() => setPaused(!paused)}>
          <Text style={styles.controlText}>{paused ? "Play" : "Pause"}</Text>
        </TouchableOpacity>
        <Text style={styles.timeText}>
          {formatTime(progress.current)} / {formatTime(progress.total)}
        </Text>
        <TouchableOpacity onPress={() => handleSeek(progress.current + 10)}>
          <Text style={styles.controlText}>+10s</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { width: "100%", aspectRatio: 16 / 9, backgroundColor: "black" },
  video: { flex: 1 },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  controls: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  controlText: { color: "white", fontSize: 16, fontWeight: "600" },
  timeText: { color: "white", fontSize: 14 },
});
```

## react-native-reanimated Animations

```tsx
// src/components/AnimatedCard.tsx
import React from "react";
import { StyleSheet, ViewStyle } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  interpolate,
  Extrapolation,
  runOnJS,
} from "react-native-reanimated";
import { Gesture, GestureDetector } from "react-native-gesture-handler";

interface AnimatedCardProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  style?: ViewStyle;
}

const SWIPE_THRESHOLD = 120;

export function AnimatedCard({
  children,
  onSwipeLeft,
  onSwipeRight,
  style,
}: AnimatedCardProps) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);

  const panGesture = Gesture.Pan()
    .onUpdate((event) => {
      translateX.value = event.translationX;
      translateY.value = event.translationY * 0.3;
    })
    .onEnd((event) => {
      if (event.translationX > SWIPE_THRESHOLD && onSwipeRight) {
        translateX.value = withTiming(400, { duration: 200 });
        runOnJS(onSwipeRight)();
      } else if (event.translationX < -SWIPE_THRESHOLD && onSwipeLeft) {
        translateX.value = withTiming(-400, { duration: 200 });
        runOnJS(onSwipeLeft)();
      } else {
        translateX.value = withSpring(0, { damping: 15, stiffness: 150 });
        translateY.value = withSpring(0, { damping: 15, stiffness: 150 });
      }
    });

  const tapGesture = Gesture.Tap()
    .onBegin(() => {
      scale.value = withSpring(0.97);
    })
    .onFinalize(() => {
      scale.value = withSpring(1);
    });

  const composed = Gesture.Simultaneous(panGesture, tapGesture);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      {
        rotate: `${interpolate(
          translateX.value,
          [-200, 0, 200],
          [-15, 0, 15],
          Extrapolation.CLAMP
        )}deg`,
      },
      { scale: scale.value },
    ],
    opacity: interpolate(
      Math.abs(translateX.value),
      [0, 200],
      [1, 0.5],
      Extrapolation.CLAMP
    ),
  }));

  return (
    <GestureDetector gesture={composed}>
      <Animated.View style={[styles.card, style, animatedStyle]}>
        {children}
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "white",
    borderRadius: 16,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
});
```

## Platform-Specific Code (iOS / Android)

### File-Based Platform Splitting

```
src/
  components/
    PermissionHandler.ios.tsx
    PermissionHandler.android.tsx
    PermissionHandler.tsx        # Fallback / web
```

### Inline Platform Checks

```tsx
// src/components/StatusBarManager.tsx
import React from "react";
import { StatusBar, Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export function StatusBarManager() {
  const insets = useSafeAreaInsets();

  return (
    <StatusBar
      barStyle="dark-content"
      backgroundColor={Platform.select({
        android: "transparent",
        ios: undefined,
      })}
      translucent={Platform.OS === "android"}
    />
  );
}
```

## Native Modules (Kotlin / Swift Bridges)

### Android Native Module (Kotlin)

```kotlin
// android/app/src/main/java/com/myapp/DeviceInfoModule.kt
package com.myapp

import android.os.Build
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.Promise

class DeviceInfoModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName() = "DeviceInfo"

    @ReactMethod
    fun getDeviceModel(promise: Promise) {
        promise.resolve("${Build.MANUFACTURER} ${Build.MODEL}")
    }

    @ReactMethod
    fun getAndroidVersion(promise: Promise) {
        promise.resolve(Build.VERSION.SDK_INT.toString())
    }
}
```

### iOS Native Module (Swift)

```swift
// ios/MyApp/DeviceInfoModule.swift
import Foundation
import UIKit

@objc(DeviceInfoModule)
class DeviceInfoModule: NSObject {

  @objc
  func getDeviceModel(_ resolve: @escaping RCTPromiseResolveBlock,
                       rejecter reject: @escaping RCTPromiseRejectBlock) {
    resolve(UIDevice.current.model)
  }

  @objc
  func getIOSVersion(_ resolve: @escaping RCTPromiseResolveBlock,
                      rejecter reject: @escaping RCTPromiseRejectBlock) {
    resolve(UIDevice.current.systemVersion)
  }

  @objc
  static func requiresMainQueueSetup() -> Bool { return false }
}
```

### JavaScript Bridge

```typescript
// src/native/DeviceInfo.ts
import { NativeModules, Platform } from "react-native";

const { DeviceInfo } = NativeModules;

export async function getDeviceModel(): Promise<string> {
  return DeviceInfo.getDeviceModel();
}

export async function getOSVersion(): Promise<string> {
  if (Platform.OS === "android") {
    return DeviceInfo.getAndroidVersion();
  }
  return DeviceInfo.getIOSVersion();
}
```

## Testing with Jest + Testing Library

```tsx
// src/components/__tests__/VideoPlayer.test.tsx
import React from "react";
import { render, fireEvent, waitFor } from "@testing-library/react-native";
import { VideoPlayer } from "../VideoPlayer";

// Mock react-native-video
jest.mock("react-native-video", () => {
  const React = require("react");
  const { View } = require("react-native");
  return React.forwardRef((props: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({
      seek: jest.fn(),
    }));
    // Simulate load after mount
    React.useEffect(() => {
      props.onLoad?.({ duration: 120 });
    }, []);
    return <View testID="mock-video" />;
  });
});

describe("VideoPlayer", () => {
  it("renders and shows loading initially", () => {
    const { getByTestId } = render(
      <VideoPlayer uri="https://example.com/video.mp4" title="Test Video" />
    );
    expect(getByTestId("mock-video")).toBeTruthy();
  });

  it("toggles play/pause on button press", async () => {
    const { getByText } = render(
      <VideoPlayer uri="https://example.com/video.mp4" title="Test Video" />
    );
    await waitFor(() => expect(getByText("Pause")).toBeTruthy());
    fireEvent.press(getByText("Pause"));
    expect(getByText("Play")).toBeTruthy();
  });
});
```

### Testing Zustand Stores

```typescript
// src/stores/__tests__/auth.test.ts
import { useAuthStore } from "../auth";

// Reset store state between tests
beforeEach(() => {
  useAuthStore.setState({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
  });
});

describe("AuthStore", () => {
  it("sets user on successful login", async () => {
    global.fetch = jest.fn().mockResolvedValueOnce({
      json: () =>
        Promise.resolve({
          user: { id: "1", name: "Alice", email: "a@b.com", avatarUrl: null },
          token: "jwt-token",
        }),
    });

    await useAuthStore.getState().login("a@b.com", "pass");
    const state = useAuthStore.getState();

    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.name).toBe("Alice");
    expect(state.token).toBe("jwt-token");
  });

  it("clears state on logout", () => {
    useAuthStore.setState({ isAuthenticated: true, token: "abc" });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().token).toBeNull();
  });
});
```

## Metro Bundler Configuration

```javascript
// metro.config.js
const { getDefaultConfig, mergeConfig } = require("@react-native/metro-config");

const defaultConfig = getDefaultConfig(__dirname);

const config = {
  resolver: {
    // Support additional file extensions
    sourceExts: [...defaultConfig.resolver.sourceExts, "cjs", "mjs"],
    // Alias for monorepo packages
    extraNodeModules: {
      "@shared": `${__dirname}/../packages/shared/src`,
    },
  },
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true, // Improves startup time
      },
    }),
  },
  // Watch additional directories in monorepo
  watchFolders: [`${__dirname}/../packages/shared`],
};

module.exports = mergeConfig(defaultConfig, config);
```

## Release Builds

### Android Signing

```groovy
// android/app/build.gradle
android {
    signingConfigs {
        release {
            storeFile file(MYAPP_RELEASE_STORE_FILE)
            storePassword MYAPP_RELEASE_STORE_PASSWORD
            keyAlias MYAPP_RELEASE_KEY_ALIAS
            keyPassword MYAPP_RELEASE_KEY_PASSWORD
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro"
        }
    }
}
```

```properties
# android/gradle.properties
MYAPP_RELEASE_STORE_FILE=my-release-key.keystore
MYAPP_RELEASE_KEY_ALIAS=my-key-alias
MYAPP_RELEASE_STORE_PASSWORD=********
MYAPP_RELEASE_KEY_PASSWORD=********
```

Build commands:

```bash
# Generate release APK
cd android && ./gradlew assembleRelease

# Generate release AAB (for Google Play)
cd android && ./gradlew bundleRelease
```

### iOS Provisioning and Archiving

```bash
# Install pods
cd ios && pod install

# Build archive via xcodebuild
xcodebuild -workspace ios/MyApp.xcworkspace \
  -scheme MyApp \
  -configuration Release \
  -archivePath build/MyApp.xcarchive \
  archive

# Export IPA
xcodebuild -exportArchive \
  -archivePath build/MyApp.xcarchive \
  -exportPath build/ipa \
  -exportOptionsPlist ios/ExportOptions.plist
```

ExportOptions.plist for App Store distribution:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store</string>
    <key>teamID</key>
    <string>YOUR_TEAM_ID</string>
    <key>uploadSymbols</key>
    <true/>
    <key>compileBitcode</key>
    <false/>
</dict>
</plist>
```

## Key Principles

1. **Type everything** -- Use TypeScript strictly. Define param lists for navigation, props for components, and shapes for stores.
2. **Keep screens thin** -- Screens should compose components and connect to stores. Business logic lives in stores or hooks.
3. **Minimize re-renders** -- Use Zustand selectors (`useStore(s => s.field)`) rather than subscribing to the entire store. Use `React.memo` for list items.
4. **Test behavior, not implementation** -- Use Testing Library queries (`getByText`, `getByRole`) rather than test IDs wherever possible.
5. **Handle permissions gracefully** -- Always check and request permissions before accessing camera, location, or storage. Show a clear explanation to the user.
6. **Profile on real devices** -- The iOS simulator and Android emulator do not reflect real performance. Always profile animations and heavy lists on physical devices.
