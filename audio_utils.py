import pygame
import pygame._sdl2 as sdl2

def query_devices():
    """
    Returns/prints the names of available input and output devices
    """
    pygame.init()
    is_capture = 0  # zero to request playback devices, non-zero to request recording devices
    num = sdl2.get_num_audio_devices(is_capture)
    output_device_names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num)]
    is_capture = 1  # zero to request playback devices, non-zero to request recording devices
    num = sdl2.get_num_audio_devices(is_capture)
    input_device_names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num)]
    print("\n".join(output_device_names))
    print("\n".join(input_device_names))
    pygame.quit()
    return {"output": output_device_names, "input": input_device_names}