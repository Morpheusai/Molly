#!/bin/bash

# 清除指定unionid下所有数据的脚本（彻底物理删除）
# unionid已写死：o5RHO60-GwKhZ7tZI6K1Z0utcfks

DB_USER="molly"
DB_PASS="molly@2025"
DB_NAME="molly_formal"
UNIONID="o5RHO60-GwKhZ7tZI6K1Z0utcfks"

# 直接执行彻底物理删除SQL
mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" <<EOF
-- 1. 删除该用户所有项目下的所有病人相关数据
DELETE FROM tools WHERE conversation_id IN (
    SELECT id FROM conversations WHERE patient_id IN (
        SELECT id FROM patients WHERE project_id IN (
            SELECT id FROM projects WHERE created_by = '$UNIONID'
        )
    )
);
DELETE FROM questions WHERE conversation_id IN (
    SELECT id FROM conversations WHERE patient_id IN (
        SELECT id FROM patients WHERE project_id IN (
            SELECT id FROM projects WHERE created_by = '$UNIONID'
        )
    )
);
DELETE FROM messages WHERE conversation_id IN (
    SELECT id FROM conversations WHERE patient_id IN (
        SELECT id FROM patients WHERE project_id IN (
            SELECT id FROM projects WHERE created_by = '$UNIONID'
        )
    )
);
DELETE FROM conversations WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '$UNIONID'
    )
);
DELETE FROM prediction_details WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '$UNIONID'
    )
);
DELETE FROM predictions WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '$UNIONID'
    )
);
DELETE FROM workflows WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '$UNIONID'
    )
);
DELETE FROM files WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '$UNIONID'
    )
);
DELETE FROM patients WHERE project_id IN (
    SELECT id FROM projects WHERE created_by = '$UNIONID'
);

-- 2. 删除该用户直接相关的数据
DELETE FROM files WHERE upload_by = '$UNIONID';
DELETE FROM user_tokens WHERE unionid = '$UNIONID';
DELETE FROM patients WHERE created_by = '$UNIONID';

-- 3. 删除该用户创建的项目
DELETE FROM projects WHERE created_by = '$UNIONID';

-- 4. 删除该用户本身
DELETE FROM users WHERE unionid = '$UNIONID';
EOF

echo "=== 数据清除完成 ==="
echo "已彻底物理删除unionid: $UNIONID 下的所有相关数据" 