# Referencia del Rol 2

Instrumento elegido para esta implementación: piano, nota La4 (MIDI 69,
440 Hz nominales), dinámica mezzoforte. El grupo puede cambiarlo después;
el pitch de `NOTA_REFERENCIA` debe coincidir con el nuevo audio.

Fuente: University of Iowa Musical Instrument Samples, Lawrence Fritts.
Piano Steinway & Sons model B, intérprete Evan Mazunik; grabación de noviembre
de 2001. La colección permite descargar y usar las muestras sin restricciones:
https://theremin.music.uiowa.edu/MIS.html

Ficha: https://theremin.music.uiowa.edu/MISpiano.html

Original descargado el 20 de octubre de 2026:
https://theremin.music.uiowa.edu/sound%20files/MIS/Piano_Other/piano/Piano.mf.A4.aiff

Preparación de `referencia.wav` (no se necesita red al ejecutar el proyecto):

1. Leer AIFF estéreo a 44100 Hz con soundfile y promediar los canales.
2. Remuestrear a 22050 Hz con `scipy.signal.resample_poly(y, 22050, 44100)`.
3. Localizar la primera muestra que supera 1% del pico absoluto y retroceder
   110 muestras (5 ms); el inicio resultante fue la muestra 5048 (0.228934 s).
4. Tomar 22050 muestras (1 segundo), normalizar el pico a 0.95 y aplicar
   desvanecimiento lineal en las últimas 110 muestras para evitar un corte brusco.
5. Guardar mono, WAV PCM de 16 bits a 22050 Hz.

El pico de FFT observado es aproximadamente 441.4 Hz (resolución 1.35 Hz),
compatible con La4. Es una grabación real, no un gen sintético conocido: no se
espera fitness 1 con el sintetizador limitado a ocho armónicos. Por eso el módulo
no expone `GEN_REFERENCIA`; los notebooks existentes leen el WAV real.
