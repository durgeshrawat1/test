// Domain Model for User
export interface UserProfile {
  id: string;
  email: string;
  name: string;
  groups: string[]; // e.g. ["Admin", "Finance", "Market"]
}

// Domain Model for Schemas (Metadata)
export interface DataSchema {
  id: string;
  name: string;        // e.g. "Mortgage Applications"
  description: string;
  accessGroup: string; // The AD Group required to see this
  columns: SchemaColumn[];
}

export interface SchemaColumn {
  name: string;
  label: string;
  dataType: 'text' | 'number' | 'date' | 'boolean' | 'currency';
  required: boolean;
}

// Generic API Response
export interface ApiResponse<T> {
  data: T;
  error?: string;
}
