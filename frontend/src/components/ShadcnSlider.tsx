import * as SliderPrimitive from "@radix-ui/react-slider";
import { Box, Typography } from "@mui/material";

interface ShadcnSliderProps {
  value: number[];
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  onValueChange: (val: number[]) => void;
}

export default function ShadcnSlider({
  value,
  min = 0,
  max = 100,
  step = 1,
  label,
  onValueChange,
}: ShadcnSliderProps) {
  return (
    <Box>
      {label && (
        <Typography variant="caption" color="text.secondary">
          {label}: {value[0]}
        </Typography>
      )}
      <SliderPrimitive.Root
        className="shadcn-slider"
        value={value}
        min={min}
        max={max}
        step={step}
        onValueChange={onValueChange}
      >
        <SliderPrimitive.Track className="shadcn-slider-track">
          <SliderPrimitive.Range className="shadcn-slider-range" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb className="shadcn-slider-thumb" />
      </SliderPrimitive.Root>
    </Box>
  );
}

