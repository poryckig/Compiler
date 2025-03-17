#!/bin/bash

cd "$(dirname "$0")/.."

mkdir -p src/parser/generated

ANTLR_JAR="$(pwd)/tools/antlr-4.13.2-complete.jar"

if [ ! -f "$ANTLR_JAR" ]; then
  echo "Błąd: Nie znaleziono pliku $ANTLR_JAR"
  echo "Pobierz plik z https://www.antlr.org/download/antlr-4.13.2-complete.jar i umieść go w katalogu tools/"
  exit 1
fi

java -jar "$ANTLR_JAR" -Dlanguage=Python3 -visitor grammar/lang.g4 -o src/parser/generated

echo "Pliki parsera zostały wygenerowane w src/parser/generated/"