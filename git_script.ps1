param ($message="too busy to provide commit details")
git add --all
git commit -m $message
git push origin master
