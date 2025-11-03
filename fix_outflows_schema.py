"""
Script para corrigir o schema da tabela outflows_outflow
Aplica as alterações da migration 0005 diretamente no banco de dados
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.db import connection

def fix_outflows_schema():
    with connection.cursor() as cursor:
        print("Iniciando correção do schema outflows_outflow...")
        
        # Desabilitar foreign keys temporariamente
        print("0. Desabilitando foreign keys temporariamente...")
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Verificar se a coluna outflow_type já existe
        cursor.execute("PRAGMA table_info(outflows_outflow)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'outflow_type' in columns:
            print("✅ Coluna outflow_type já existe!")
            cursor.execute("PRAGMA foreign_keys = ON")
            return
        
        print(f"Colunas atuais: {columns}")
        
        # Passo 1: Renomear tabela antiga
        print("\n1. Renomeando tabela antiga...")
        cursor.execute("ALTER TABLE outflows_outflow RENAME TO outflows_outflow_old")
        
        # Passo 2: Criar nova tabela com estrutura correta
        print("2. Criando nova tabela com estrutura correta...")
        cursor.execute("""
            CREATE TABLE outflows_outflow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outflow_type VARCHAR(20) NOT NULL,
                description TEXT NOT NULL,
                recipient VARCHAR(200),
                created_by_id INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (created_by_id) REFERENCES auth_user (id)
            )
        """)
        
        # Passo 3: Migrar dados existentes (se houver)
        print("3. Verificando dados existentes...")
        cursor.execute("SELECT COUNT(*) FROM outflows_outflow_old")
        count = cursor.fetchone()[0]
        print(f"   Encontrados {count} registros na tabela antiga")
        
        if count > 0:
            print("4. Migrando dados (definindo tipo padrão 'other')...")
            cursor.execute("""
                INSERT INTO outflows_outflow 
                (id, outflow_type, description, recipient, created_by_id, created_at, updated_at)
                SELECT 
                    id,
                    'other' as outflow_type,
                    COALESCE(description, 'Migração de dados antigos') as description,
                    NULL as recipient,
                    NULL as created_by_id,
                    created_at,
                    updated_at
                FROM outflows_outflow_old
            """)
            print(f"   ✅ {count} registros migrados com sucesso!")
        
        # Passo 4: Atualizar tabela de itens
        print("\n5. Atualizando tabela outflows_outflowitem...")
        
        # Verificar se coluna notes já existe
        cursor.execute("PRAGMA table_info(outflows_outflowitem)")
        item_columns = [col[1] for col in cursor.fetchall()]
        
        if 'notes' not in item_columns:
            print("   Adicionando coluna 'notes'...")
            cursor.execute("""
                ALTER TABLE outflows_outflowitem 
                ADD COLUMN notes TEXT
            """)
            print("   ✅ Coluna 'notes' adicionada!")
        else:
            print("   ✅ Coluna 'notes' já existe!")
        
        # Passo 5: Remover tabela antiga
        print("\n6. Removendo tabela antiga...")
        cursor.execute("DROP TABLE outflows_outflow_old")
        
        # Reabilitar foreign keys
        print("\n7. Reabilitando foreign keys...")
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("\n✅ Schema corrigido com sucesso!")
        print("\nPróximos passos:")
        print("1. Reinicie o servidor Django")
        print("2. Acesse http://localhost:8000/outflows/")
        print("3. Se houver dados migrados, revise e atualize o tipo de saída apropriado")

if __name__ == '__main__':
    try:
        fix_outflows_schema()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
