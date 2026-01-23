// src/types/index.ts

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  groups: string[]; // e.g. ["Admin", "Finance_Read", "Market_Write"]
}

// A "Schema" represents a user-defined table (e.g., "Mortgage_Applications")
export interface DataSchema {
  id: string;
  name: string; // Display name
  description: string;
  accessGroup: string; // The AD Group required to see/edit this
  columns: SchemaColumn[];
}

export interface SchemaColumn {
  name: string;
  dataType: 'text' | 'number' | 'date' | 'boolean';
  required: boolean;
}

// Standard API Response wrapper
export interface ApiResponse<T> {
  data: T;
  error?: string;
}
