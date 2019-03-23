python -m zipfile -c src.zip src/*
echo -e '#!'`which python`'\n' > srcapp
cat src.zip >> srcapp
chmod +x srcapp

