CLI
=======


# To execute with the controller module

```
python server.py --control
```


# To load a program

```
echo '{"program_path": "AV_vs_Air.csv"}' | curl -d @- localhost:9000/load_program
```


# To run a program

```
curl localhost:9000/controls/record
```


