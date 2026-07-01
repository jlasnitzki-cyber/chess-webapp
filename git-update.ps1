param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

git status
git add .
git commit -m $Message
git push

#run: .\git-update.ps1 "Fix Vercel build"
#if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned