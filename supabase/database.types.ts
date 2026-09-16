// Generated from Supabase project ivmkvwudblcqhtoiqlaf after migration
// land_records_foundation. Do not edit by hand — regenerate via
// Supabase type generation. Covers all 12 MVP tables.
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      audit_logs: {
        Row: {
          action: string
          entity_id: string | null
          entity_type: string
          id: string
          metadata: Json
          new_value: Json | null
          old_value: Json | null
          timestamp: string
          user_id: string | null
        }
        Insert: {
          action: string
          entity_id?: string | null
          entity_type: string
          id?: string
          metadata?: Json
          new_value?: Json | null
          old_value?: Json | null
          timestamp?: string
          user_id?: string | null
        }
        Update: {
          action?: string
          entity_id?: string | null
          entity_type?: string
          id?: string
          metadata?: Json
          new_value?: Json | null
          old_value?: Json | null
          timestamp?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_logs_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          checksum: string
          created_at: string
          document_type: string | null
          file_name: string
          file_size: number
          file_type: string
          id: string
          language: string | null
          processing_status: string
          storage_path: string
          updated_at: string
          uploaded_at: string
          uploaded_by: string | null
        }
        Insert: {
          checksum: string
          created_at?: string
          document_type?: string | null
          file_name: string
          file_size: number
          file_type: string
          id?: string
          language?: string | null
          processing_status?: string
          storage_path: string
          updated_at?: string
          uploaded_at?: string
          uploaded_by?: string | null
        }
        Update: {
          checksum?: string
          created_at?: string
          document_type?: string | null
          file_name?: string
          file_size?: number
          file_type?: string
          id?: string
          language?: string | null
          processing_status?: string
          storage_path?: string
          updated_at?: string
          uploaded_at?: string
          uploaded_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "documents_uploaded_by_fkey"
            columns: ["uploaded_by"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      extracted_fields: {
        Row: {
          bounding_box: Json | null
          confidence: number | null
          created_at: string
          extraction_status: string
          field_name: string
          id: string
          land_record_id: string
          source_page: number | null
          source_text: string | null
          validation_status: string
          value: string | null
        }
        Insert: {
          bounding_box?: Json | null
          confidence?: number | null
          created_at?: string
          extraction_status?: string
          field_name: string
          id?: string
          land_record_id: string
          source_page?: number | null
          source_text?: string | null
          validation_status?: string
          value?: string | null
        }
        Update: {
          bounding_box?: Json | null
          confidence?: number | null
          created_at?: string
          extraction_status?: string
          field_name?: string
          id?: string
          land_record_id?: string
          source_page?: number | null
          source_text?: string | null
          validation_status?: string
          value?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "extracted_fields_land_record_id_fkey"
            columns: ["land_record_id"]
            isOneToOne: false
            referencedRelation: "land_records"
            referencedColumns: ["id"]
          },
        ]
      }
      field_corrections: {
        Row: {
          changed_at: string
          changed_by: string | null
          field_name: string
          id: string
          land_record_id: string
          new_value: string | null
          old_value: string | null
          reason: string | null
        }
        Insert: {
          changed_at?: string
          changed_by?: string | null
          field_name: string
          id?: string
          land_record_id: string
          new_value?: string | null
          old_value?: string | null
          reason?: string | null
        }
        Update: {
          changed_at?: string
          changed_by?: string | null
          field_name?: string
          id?: string
          land_record_id?: string
          new_value?: string | null
          old_value?: string | null
          reason?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "field_corrections_changed_by_fkey"
            columns: ["changed_by"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "field_corrections_land_record_id_fkey"
            columns: ["land_record_id"]
            isOneToOne: false
            referencedRelation: "land_records"
            referencedColumns: ["id"]
          },
        ]
      }
      land_records: {
        Row: {
          approved_at: string | null
          approved_by: string | null
          area: number | null
          area_unit: string | null
          created_at: string
          district: string | null
          document_id: string
          father_or_spouse_name: string | null
          id: string
          khasra_number: string | null
          khata_number: string | null
          land_classification: string | null
          mutation_number: string | null
          owner_name: string | null
          record_date: string | null
          registration_number: string | null
          status: string
          survey_number: string | null
          tehsil: string | null
          updated_at: string
          village: string | null
        }
        Insert: {
          approved_at?: string | null
          approved_by?: string | null
          area?: number | null
          area_unit?: string | null
          created_at?: string
          district?: string | null
          document_id: string
          father_or_spouse_name?: string | null
          id?: string
          khasra_number?: string | null
          khata_number?: string | null
          land_classification?: string | null
          mutation_number?: string | null
          owner_name?: string | null
          record_date?: string | null
          registration_number?: string | null
          status?: string
          survey_number?: string | null
          tehsil?: string | null
          updated_at?: string
          village?: string | null
        }
        Update: {
          approved_at?: string | null
          approved_by?: string | null
          area?: number | null
          area_unit?: string | null
          created_at?: string
          district?: string | null
          document_id?: string
          father_or_spouse_name?: string | null
          id?: string
          khasra_number?: string | null
          khata_number?: string | null
          land_classification?: string | null
          mutation_number?: string | null
          owner_name?: string | null
          record_date?: string | null
          registration_number?: string | null
          status?: string
          survey_number?: string | null
          tehsil?: string | null
          updated_at?: string
          village?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "land_records_approved_by_fkey"
            columns: ["approved_by"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "land_records_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: true
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      ocr_results: {
        Row: {
          created_at: string
          document_id: string
          id: string
          ocr_confidence: number | null
          page_number: number
          structured_output_reference: Json
          text: string
        }
        Insert: {
          created_at?: string
          document_id: string
          id?: string
          ocr_confidence?: number | null
          page_number: number
          structured_output_reference?: Json
          text?: string
        }
        Update: {
          created_at?: string
          document_id?: string
          id?: string
          ocr_confidence?: number | null
          page_number?: number
          structured_output_reference?: Json
          text?: string
        }
        Relationships: [
          {
            foreignKeyName: "ocr_results_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      processing_jobs: {
        Row: {
          completed_at: string | null
          created_at: string
          document_id: string
          error_code: string | null
          error_message: string | null
          id: string
          pipeline_version: string
          started_at: string | null
          status: string
        }
        Insert: {
          completed_at?: string | null
          created_at?: string
          document_id: string
          error_code?: string | null
          error_message?: string | null
          id?: string
          pipeline_version?: string
          started_at?: string | null
          status?: string
        }
        Update: {
          completed_at?: string | null
          created_at?: string
          document_id?: string
          error_code?: string | null
          error_message?: string | null
          id?: string
          pipeline_version?: string
          started_at?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "processing_jobs_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      reference_data: {
        Row: {
          code: string
          created_at: string
          id: string
          name: string
          parent_id: string | null
          reference_type: string
          status: string
          version: string
        }
        Insert: {
          code?: string
          created_at?: string
          id?: string
          name: string
          parent_id?: string | null
          reference_type: string
          status?: string
          version?: string
        }
        Update: {
          code?: string
          created_at?: string
          id?: string
          name?: string
          parent_id?: string | null
          reference_type?: string
          status?: string
          version?: string
        }
        Relationships: [
          {
            foreignKeyName: "reference_data_parent_id_fkey"
            columns: ["parent_id"]
            isOneToOne: false
            referencedRelation: "reference_data"
            referencedColumns: ["id"]
          },
        ]
      }
      review_tasks: {
        Row: {
          assigned_to: string | null
          completed_at: string | null
          created_at: string
          id: string
          land_record_id: string
          priority: string
          reason: string | null
          status: string
        }
        Insert: {
          assigned_to?: string | null
          completed_at?: string | null
          created_at?: string
          id?: string
          land_record_id: string
          priority?: string
          reason?: string | null
          status?: string
        }
        Update: {
          assigned_to?: string | null
          completed_at?: string | null
          created_at?: string
          id?: string
          land_record_id?: string
          priority?: string
          reason?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "review_tasks_assigned_to_fkey"
            columns: ["assigned_to"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "review_tasks_land_record_id_fkey"
            columns: ["land_record_id"]
            isOneToOne: false
            referencedRelation: "land_records"
            referencedColumns: ["id"]
          },
        ]
      }
      roles: {
        Row: {
          created_at: string
          id: string
          name: string
          permissions: Json
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          permissions?: Json
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          permissions?: Json
        }
        Relationships: []
      }
      users: {
        Row: {
          auth_id: string | null
          created_at: string
          email: string
          id: string
          name: string
          password_hash: string | null
          role: string
          status: string
          updated_at: string
        }
        Insert: {
          auth_id?: string | null
          created_at?: string
          email: string
          id?: string
          name: string
          password_hash?: string | null
          role: string
          status?: string
          updated_at?: string
        }
        Update: {
          auth_id?: string | null
          created_at?: string
          email?: string
          id?: string
          name?: string
          password_hash?: string | null
          role?: string
          status?: string
          updated_at?: string
        }
        Relationships: []
      }
      validation_results: {
        Row: {
          created_at: string
          field_name: string | null
          id: string
          land_record_id: string
          message: string
          rule_id: string
          severity: string
          status: string
        }
        Insert: {
          created_at?: string | null
          field_name?: string | null
          id?: string
          land_record_id: string
          message: string
          rule_id: string
          severity: string
          status: string
        }
        Update: {
          created_at?: string | null
          field_name?: string | null
          id?: string
          land_record_id?: string
          message?: string | null
          rule_id?: string | null
          severity?: string | null
          status?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "validation_results_land_record_id_fkey"
            columns: ["land_record_id"]
            isOneToOne: false
            referencedRelation: "land_records"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]][DefaultSchemaEnumNameOrOptions]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
