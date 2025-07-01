#!/bin/bash

# MySQL 数据库配置
DB_USER="molly"
DB_PASS="molly@2025"
DB_NAME="molly_formal"

# 要删除的用户ID（unionid）
USER_ID="o5RHO6-7_IVUMfR96-UP2loYvLN8"

SQL=$(cat <<EOF
START TRANSACTION;

-- 1. 删除 questions（通过 messages → conversations → patients → projects → users）
DELETE FROM questions WHERE message_id IN (
    SELECT id FROM messages WHERE conversation_id IN (
        SELECT id FROM conversations WHERE patient_id IN (
            SELECT id FROM patients WHERE project_id IN (
                SELECT id FROM projects WHERE created_by = '${USER_ID}'
            )
        )
    )
);

-- 2. 删除 messages
DELETE FROM messages WHERE conversation_id IN (
    SELECT id FROM conversations WHERE patient_id IN (
        SELECT id FROM patients WHERE project_id IN (
            SELECT id FROM projects WHERE created_by = '${USER_ID}'
        )
    )
);

-- 3. 删除 conversations
DELETE FROM conversations WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '${USER_ID}'
    )
);

-- 4. 删除 prediction_details
DELETE FROM prediction_details WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '${USER_ID}'
    )
);

-- 5. 删除 predictions
DELETE FROM predictions WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '${USER_ID}'
    )
);

-- 6. 删除 workflows（patient_id 关联）
DELETE FROM workflows WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '${USER_ID}'
    )
);

-- 7. 删除 workflows（started_by、completed_by 关联）
DELETE FROM workflows WHERE started_by = '${USER_ID}';
DELETE FROM workflows WHERE completed_by = '${USER_ID}';

-- 8. 删除 files（patient_id 关联）
DELETE FROM files WHERE patient_id IN (
    SELECT id FROM patients WHERE project_id IN (
        SELECT id FROM projects WHERE created_by = '${USER_ID}'
    )
);

-- 9. 删除 files（upload_by 关联）
DELETE FROM files WHERE upload_by = '${USER_ID}';

-- 10. 删除 user_tokens
DELETE FROM user_tokens WHERE unionid = '${USER_ID}';

-- 11. 删除 patients
DELETE FROM patients WHERE project_id IN (
    SELECT id FROM projects WHERE created_by = '${USER_ID}'
);
DELETE FROM patients WHERE created_by = '${USER_ID}';

-- 12. 删除 projects
DELETE FROM projects WHERE created_by = '${USER_ID}';

-- 13. 删除用户本身
DELETE FROM users WHERE unionid = '${USER_ID}';

COMMIT;
EOF
)

echo "正在删除用户 ${USER_ID} 的所有数据..."
mysql -u "${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" -e "${SQL}"

if [ $? -eq 0 ]; then
    echo "✅  用户数据删除成功"
else
    echo "❌  用户数据删除失败，请检查错误"
fi