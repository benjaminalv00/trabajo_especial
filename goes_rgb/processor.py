import numpy as np

def calibrate_imag(imagen, metadato, U = 'T'):
  canal = int(metadato['band_id'][:])
  print('Calibrando la imagen', canal)
  if canal >=7:
      #Parámetros de calibracion
      fk1 = metadato['planck_fk1'].values # DN -> K
      fk2 = metadato['planck_fk2'].values
      bc1 = metadato['planck_bc1'].values
      bc2 = metadato['planck_bc2'].values

      imag_cal = (fk2 / (np.log((fk1 / imagen) + 1)) - bc1 ) / bc2 - 273.15 # K -> C
      Unit = "Temperatura de Brillo [°C]"
  elif U=='Rad':
      pendiente= metadato['Rad'].scale_factor
      ordenada= metadato['Rad'].add_offset
      imag_cal =imagen*pendiente+ordenada
      Unit = "Radiancia ["+metadato['Rad'].units+"]"
  elif U=='Ref':
      raise("Not implemented yet")
      kapa0 = metadato2['kappa0'][0].data
      imag_cal = kapa0 * imagen
      Unit = "Reflectancia"
  return imag_cal