import stscraper as scraper
from github_api import GitHubAPI
import csv
import mysql.connector

if __name__ == "__main__":
    api = GitHubAPI()
    strApi = scraper.GitHubAPI("enter_github_token")

    # FILES FOR OUTPUT
    #outputFile = open("cross-referenced-prs.txt","a")
    csvOutputFile = open("cross-referenced-prs.csv","w",encoding="utf-8")
    writer = csv.writer(csvOutputFile)
    writer.writerow(['repo1','PR1','PR1_author', 'PR1_reviewers (before PR1 is closed)', 'PR1_CreateAt', 'PR1_ClosedAt', 'isClosed', 'PR1_closedBy', 'isIssue','repo2', 'PR2','PR2_author',
                     'PR2_CreateAt', 'PR2_ClosedAt', 'PR2_isIssue', 'isCrossRepo', 'beforePR1Closed','crossRefByWhom', 'crossComment'])

    csvRepoIndexFile = open("indexed-repo-list.csv","w",encoding="utf-8")
    writerForRepos = csv.writer(csvRepoIndexFile)
    writerForRepos.writerow(['repoIndex', 'repoName'])


    # Connect to mysql to export results 
    connection = mysql.connector.connect(host='enter_host_name', database='enter_database_name', user='enter_user_name', password='enter_password')
    cursor = connection.cursor()

    # Getting list of repos with more than 500 prs from a csv file to a text file
    csv_file = r"path_to_csv_file_with_repo_list"
    txt_file = r"path_to_a_blank_text_file"
    my_input_file = open(csv_file, "r")
    csv_reader = csv.reader(my_input_file)
    next(csv_reader)
    with open(txt_file, "w") as my_output_file:
        with my_input_file:
            [my_output_file.write(" ".join(row) + '\n') for row in csv_reader]
        my_output_file.close()

    # READING FROM FILE
    repoListFile = open(r"path_to_text_file_with_repo_list","r")
    repoList = []
    # Go through each repository in the list one at a time
    for repo in repoListFile:

        repo = repo.rstrip()
        pageNumber = 0
        prCount = 0

        # If this repo hasn't already been added to the indexed repo list, add it
        if (repo in repoList) == False:
            repoList.append(repo)
            writerForRepos.writerow([repoList.index(repo),repo])

            # Output repo and its index to table on mysql
            mySql_insert_query_repos = """INSERT INTO indexed_repos VALUES (%s, %s)"""
            repoListValues = (str(repoList.index(repo)), repo)
            cursor.execute(mySql_insert_query_repos, repoListValues)
            connection.commit()

        # Determine total number of pulls+issues in repo
        totalPulls = len(list(strApi.repo_pulls(repo))) + len(list(strApi.repo_issues(repo)))

        # Keep repeating as long as there are more prs
        while prCount != totalPulls:

            # Increment page number
            pageNumber = pageNumber+1

            # Retrieve all prs on current page number
            prUrl = "repos/%s/issues?state=all&page=%d" % (repo, pageNumber)
            allPulls = api.request(prUrl)


            #outputFile.write("[%s" % repo)

            # Loop through each pr on this page number
            for pr in allPulls:
                prCount = prCount + 1
                pr_id = pr.get("number")
                allEvents = api.get_issue_pr_timeline(repo, pr_id)

                prClosed = False
                reviewers = []

                # Obtain list of reviewers (before pr is closed) by going through each event
                for event in allEvents:
                    if event.get("event") == "closed":
                        prClosed = True
                        break

                    if event.get("event") == "commented" or event.get("event") == "reviewed":
                        if prClosed == False:
                            if event.get("user") == None:
                                reviewers.append("deleted account")
                            else:
                                if (event.get("user").get("login") in reviewers) == False:
                                    reviewers.append(event.get("user").get("login"))


                # Reset closed status of pr to false
                prClosed = False

                # Go through each event of pr
                for event in allEvents:

                    # Change closed status of pr to true if event is labelled as "closed"
                    if event.get("event") == "closed":
                        prClosed = True

                    # If the pr has been cross referenced
                    if event.get("event") == "cross-referenced":
                        #outputFile.write(", %s" % pr_id)

                        # Determine the status of the PR (open or closed)
                        if (pr.get("state") == 'closed'):
                            isClosed = 'Y'
                        else:
                            isClosed = 'N'

                        # Determine if pr is an issue
                        if "/issues/"+str(pr_id) in pr.get("html_url"):
                            isIssue = 'Y'
                        else:
                            isIssue = 'N'

                        # Find the source (The issue or pull request that added a cross-reference)
                        source = event.get("source")

                        # Determine if the source of cross-reference is an issue
                        if "/issues/"+str(source.get("issue").get("number")) in source.get("issue").get("html_url"):
                            isIssuePR2 = 'Y'
                        else:
                            isIssuePR2 = 'N'

                        # Determine if it is a cross repository reference and add repo to indexed list if it is
                        repo2 = source.get("issue").get("repository").get("full_name")
                        if repo == repo2:
                            isCrossRepo = 'N'
                        else:
                            isCrossRepo = 'Y'
                            # If the repo hasn't already been added to the indexed list, add it
                            if (repo2 in repoList) == False:
                                repoList.append(repo2)
                                writerForRepos.writerow([repoList.index(repo2), repo2])

                                #output repo and its index to table on mysql
                                mySql_insert_query_repos = """INSERT INTO indexed_repos VALUES (%s, %s)"""
                                repoListValues = (str(repoList.index(repo2)), repo2)
                                cursor.execute(mySql_insert_query_repos, repoListValues)
                                connection.commit()

                        # Determine if pr is cross referenced before it is closed
                        if prClosed:
                            beforePR1Closed = 'N'
                        else:
                            beforePR1Closed = 'Y'

                        # Find urls of both prs
                        pr1Url = pr.get("html_url")
                        pr2Url = source.get("issue").get("html_url")

                        # Determine author of pr1
                        if pr.get("user") != None:
                            pr1Author = pr.get("user").get("login")
                        else:
                            pr1Author = "deleted account"

                        # Determine author of pr1
                        if source.get("issue").get("user") != None:
                            pr2Author = source.get("issue").get("user").get("login")
                        else:
                            pr2Author = "deleted account"

                        # Determine creation and closing time of pr1 and closed by whom
                        pr1CreateAt = pr.get("created_at")
                        if isClosed:
                            pr1ClosedAt = pr.get("closed_at")

                            issueUrl = "repos/%s/issues/%d" % (repo, pr_id)
                            if api.request(issueUrl).get("closed_by") != None:
                                pr1ClosedBy = api.request(issueUrl).get("closed_by").get("login")
                            else:
                                pr1ClosedBy = "deleted account"

                        else:
                            pr1ClosedAt = '-'
                            pr1ClosedBy = '-'

                        # Determine creation and closing time of pr2
                        pr2CreateAt = source.get("issue").get("created_at")
                        pr2ClosedAt = source.get("issue").get("closed_at")

                        # Get the person who cross referenced it
                        if event.get("actor") != None:
                            crossRefByWhom = event.get("actor").get("login")
                        else:
                            crossRefByWhom = "deleted account"

                        # Get the cross comment
                        crossComment = event.get("source").get("issue").get("body")

                        # Output data to csv file
                        writer.writerow([repoList.index(repo), pr_id, pr1Author, reviewers, pr1CreateAt, pr1ClosedAt, isClosed, pr1ClosedBy, isIssue,
                                         repoList.index(repo2),source.get("issue").get("number"),pr2Author, pr2CreateAt, pr2ClosedAt,
                                         isIssuePR2, isCrossRepo, beforePR1Closed, crossRefByWhom, crossComment])

                        # Output row of data to mysql table
                        mySql_insert_query = """INSERT INTO cross_ref_prs_table VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s, %s, %s,%s, %s, %s, %s, %s)"""
                        values = (str(repoList.index(repo)), str(pr_id), pr1Author, ', '.join(reviewers), pr1CreateAt, pr1ClosedAt, isClosed, pr1ClosedBy, isIssue,
                                         str(repoList.index(repo2)),str(source.get("issue").get("number")),pr2Author, pr2CreateAt, pr2ClosedAt,
                                         isIssuePR2, isCrossRepo, beforePR1Closed, crossRefByWhom, crossComment)
                        cursor.execute(mySql_insert_query,values)
                        connection.commit()


        #outputFile.write("]\n")

    # Close all files and connections
    repoListFile.close()
    #outputFile.close()
    csvOutputFile.close()
    csvRepoIndexFile.close()

    cursor.close()
    connection.close()
