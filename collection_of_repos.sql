SELECT
	#id AS 'repo_id',
    #COUNT(*) AS 'pr_count',
    SUBSTRING(url, 30) AS 'repo_name',
    COUNT(*) AS 'pr_count'
FROM
	(select projects.id,projects.url,projects.forked_from,projects.deleted,pull_requests.base_repo_id from projects,pull_requests 
    WHERE projects.id = pull_requests.base_repo_id) AS joined_table
WHERE (joined_table.forked_from IS NULL AND joined_table.deleted=0)
GROUP BY id
HAVING COUNT(*) >= 500
ORDER BY COUNT(*) DESC;
