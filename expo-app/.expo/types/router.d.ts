/* eslint-disable */
import * as Router from 'expo-router';

export * from 'expo-router';

declare module 'expo-router' {
  export namespace ExpoRouter {
    export interface __routes<T extends string = string> extends Record<string, unknown> {
      StaticRoutes: `/` | `/Dashboard` | `/UserInterview` | `/_sitemap` | `/auth` | `/auth/welcome` | `/summary`;
      DynamicRoutes: never;
      DynamicRouteTemplate: never;
    }
  }
}
