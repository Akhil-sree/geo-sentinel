let _polygonClicked = false;

export function setPolygonClicked() { _polygonClicked = true; }

export function consumePolygonClick(): boolean {
  if (_polygonClicked) { _polygonClicked = false; return true; }
  return false;
}
