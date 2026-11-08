# 중세 정예병 도트(Pixel Art) 배틀체스 장기: 픽셀 아트 바이블 및 프레임 모션 명세서

> **문서 버전**: v2.0 (16-Bit / 32-Bit Retro Pixel Art Remake)  
> **작성자**: 총괄 아트 디렉터 및 모션 그래픽 에이전트 (`art_director`)  
> **관련 에셋 및 모듈**:  
> - 도트 키아트 일러스트: [`assets/art/medieval_battle_janggi_key_art.jpg`](file:///home/janginwoo/Desktop/GAME/assets/art/medieval_battle_janggi_key_art.jpg)  
> - 도트 7대 기물 캐릭터 시트: [`assets/art/unit_roster_concept_sheet.jpg`](file:///home/janginwoo/Desktop/GAME/assets/art/unit_roster_concept_sheet.jpg)  
> - 인게임 도트 스프라이트 & 프레임 애니메이션 렌더러: [`src/js/art_renderer.js`](file:///home/janginwoo/Desktop/GAME/src/js/art_renderer.js) (`window.ArtRenderer` v2.0.0-PIXEL)

---

## 1. 핵심 픽셀 아트 디렉션 (16-Bit / 32-Bit Pixel Art Direction)

### 1.1 "칼각이 살아있는 정통 16-bit / 32-bit 아케이드 도트 배틀체스"
1. **100% 정수 그리드 도트 렌더링 (`ctx.imageSmoothingEnabled = false`)**:
   - 모든 부드러운 벡터 곡선(`arc`, `bezierCurveTo`)과 안티앨리어싱 블러를 완전히 배제하고, 가상 도트 버퍼(`PixelGridSurface`, 유닛 56×56 도트 그리드 / 페데스탈 36×28 도트 그리드) 위에 **1×1 정수 픽셀 블록 단위**로 래스터화한 뒤 오프스크린 캔버스에 캐싱하여 칼각으로 블리팅(`drawImage`)합니다.
2. **자동 1픽셀 다크 아웃라인 & 선택/장군 1픽셀 외곽 하이라이트 (`applyPixelOutline`)**:
   - 모든 유닛 도트 스프라이트 외곽에는 정통 도트 RPG/전략 게임 특유의 **1px 딥 다크 아웃라인(`#090c15`)**이 자동 생성됩니다.
   - 기물 선택(`isSelected`) 시에는 **1px 황금 도트 아웃라인(`#facc15`)**, 장군 위협(`isCheck`) 시에는 **1px 적색 도트 아웃라인(`#ef4444`)**이 외곽 도트를 따라 점등됩니다.
3. **체커보드 베이어 디더링(`fillDitherRect`) & 11×11 비트맵 한자 폰트(`PIXEL_HANJA_FONT`)**:
   - 갑옷의 금속 질감, 망토의 명암, 장기알 받침대의 석재/옥 질감은 `((x + y) & 1) === 0` 체커보드 도트 디더링(Checkerboard Dithering)으로 표현합니다.
   - 장기알 페데스탈 전면 명패의 한자(`楚`, `漢`, `宮`, `車`, `包`, `馬`, `象`, `士`, `卒`, `兵`)는 일반 브라우저 폰트 대신 **직접 도트로 찍은 11×11 비트맵 글리프 매트릭스(`PIXEL_HANJA_FONT`)**와 1px 드롭 섀도우로 렌더링되어 도트 일체감과 가독성을 동시에 확보했습니다.

---

## 2. 4대 중세 진영 도트 팔레트 및 스프라이트 파츠 규격 (`FACTION_SKINS`)

| 국가 코드 (`faction`) | 진영 명칭 | 도트 문양 (`PIXEL_EMBLEMS`) | 핵심 도트 팔레트 (`armorPrimary` / `armorLight` / `armorSecondary` / `gold`) | 기물별 도트 스프라이트 특징 |
| :--- | :--- | :---: | :--- | :--- |
| **`GORYEO`** | **고려 천군**<br>*(Goryeo Iron Army)* | `SAMJOKOH`<br>(9×8 삼족오 도트) | • 흑칠 철갑 (`#1e293b` / `#475569`)<br>• 감청 두정갑 (`#1d4ed8` / `#1e3a8a`)<br>• 황금 장식 (`#f59e0b` / `#fde047`) | • **궁**: 황금 익선관 + 사인참사검 광검 도트<br>• **차**: 철갑 개마무사 마갑 + 장창 & 전차 바퀴<br>• **포**: 문종 다연장 신기전 화차 & 로켓 화살촉<br>• **마**: 별무반 기병 + 마상편곤 도트<br>• **상**: 착호갑사 망루 + 철갑 전투코끼리<br>• **사**: 내금위 협도(언월도) + 호심경<br>• **졸**: 사각 팽배 방패 + 장창 보병 |
| **`TEMPLAR`** | **성전 기사단**<br>*(Royal Crusaders)* | `CROSS`<br>(9×8 십자가 도트) | • 밀라노 은갑 (`#94a3b8` / `#e2e8f0`)<br>• 백색 서코트 (`#f1f5f9`)<br>• 성전 적십자 (`#dc2626`) | • **궁**: 왕관 그레이트헬름 + 성검 도트<br>• **차**: 은빛 마갑 데스트리어 + 쿠치드 랜스<br>• **포**: A프레임 목재 평형추 트레뷰셋 & 화염석<br>• **마**: 슈거로프 헬름 + 브로드소드 기병<br>• **상**: 고딕 성채 망루 전투코끼리<br>• **사**: 타워실드(적십자) + 할버드<br>• **졸**: 챙 넓은 케틀햇 철모 + 히터실드 창병 |
| **`BYZANTINE`** | **비잔틴 제국군**<br>*(Golden Empire)* | `DOUBLE_EAGLE`<br>(9×8 쌍두독수리) | • 황금 비늘갑주 (`#d97706` / `#fbbf24`)<br>• 제국 자색 (`#6b21a8` / `#4c1d95`)<br>• 황실 순금 (`#fde047`) | • **궁**: 황제 보관 + 제국 스파타 보검<br>• **차**: 황금 가면 클리바나리 카타프락토이<br>• **포**: 청동 그리스의 불 사이펀 & 에메랄드 화염<br>• **마**: 자색 깃털 투구 타그마타 기병<br>• **상**: 황금 머리장식 제국 코끼리<br>• **사**: 바랑기안 가드 + 거대 데인액스 도끼<br>• **졸**: 타원형 스쿠톤 방패 중보병 |
| **`MAMLUK`** | **맘루크 술탄국**<br>*(Mamluk Sultanate)* | `CRESCENT`<br>(9×8 초승달 도트) | • 다마스쿠스 철 (`#334155` / `#64748b`)<br>• 터콰이즈 비단 (`#0d9488` / `#115e59`)<br>• 사막 황금 (`#fbbf24`) | • **궁**: 황금 첨탑 터번 투구 + 보석 샴시르<br>• **차**: 아라비안 중장갑 카스 창기병<br>• **포**: 사막 만자니크 투석기 & 나프트 화염탄<br>• **마**: 파리스 시미터 사막 기병<br>• **상**: 강철 상아 칼날 사라센 코끼리<br>• **사**: 안면 베일 투구 + 할카 쌍곡도<br>• **졸**: 사막 터번 + 원형 방패(Dhal) 창보병 |

---

## 3. 도트 프레임 스텝 애니메이션 명세 (`getSteppedFrameState`)

부드러운 실수(Float) 보간을 배제하고, 고전 16-bit/32-bit 아케이드 게임 특유의 **절도 있는 이산 프레임 스텝(Discrete Frame-Stepped Animation)**으로 동작합니다.

| 상태 (`state`) | 프레임 수 | 프레임 스텝 연출 상세 |
| :--- | :---: | :--- |
| **`IDLE`** | **4 Frames**<br>(220ms 간격) | • 흉곽 및 투구가 `0px → -1px → -1px → 0px` 단위로 절도 있게 숨쉬기 바운스<br>• 망토(`capeFrame`)와 등 뒤 군기(Sashimono)가 3단계 도트 패턴으로 펄럭임 |
| **`MOVE`** | **4 Frames**<br>(110ms 간격) | • 보병/기병/코끼리 다리가 `-2px → 0px → +2px → 0px` 도트 보폭으로 교차 행군<br>• 홀수 프레임마다 상체가 `-2px` 도트 바운스 |
| **`ATTACK`** | **6 Frames**<br>(`progress` 기반) | • **Frame 0~1 (Wind-up)**: 뒤로 `-3px` 물러서며 무기를 머리 위로 치켜듦 (`armPose: 'RAISED'`)<br>• **Frame 2~3 (Strike + Pixel Smear)**: 앞으로 `+5px` 돌진하며 아케이드 특유의 **3색 도트 검기 궤적(Pixel Weapon Smear)** 출력 및 화차 신기전/트레뷰셋 화염탄/궁의 8-bit 심판 번개 기둥 작렬<br>• **Frame 4~5 (Recovery)**: 타격 십자 도트 스파크 출력 후 기본 자세 복귀 |
| **`HIT`** | **6 Frames** | • 피격 경직(`-4px` 넉백)과 함께 스프라이트 전체가 **순백색(`#ffffff`) ↔ 적색(`#ef4444`) 도트 팔레트 스왑 플래시**로 깜빡임 |
| **`DEATH`** | **Pixel Shatter** | • 유닛 스프라이트가 **18개의 2×2 도트 파편 블록(Pixel Debris Shatter)**으로 사방에 튀어 흩어지며, 중앙에서 **8-bit 도트 영혼 불꽃**이 하늘로 승천함 |

---

## 4. `window.ArtRenderer` (v2.0.0-PIXEL) API 호환성 명세

기존 `main.js` 및 `battle_director.js`와의 호환성을 100% 유지합니다.

- `ArtRenderer.drawUnit(ctx, options)`: 3D 도트 팔각 장기알 페데스탈 + 11×11 비트맵 한자 명패 + 56×56 도트 정예병 스프라이트 렌더링
- `ArtRenderer.drawBoardPedestal(ctx, x, y, radius, side, type, faction, options)`: 도트 팔각 장기알 받침대 단독 렌더링
- `ArtRenderer.drawBattleScene(ctx, duel)`: 도트 벽돌 성채 결투장 배경 + 2.3배 확대 도트 유닛 대결 + 도트 신기전/화염석 포물선 폭격 + 스텝 카메라 쉐이크 렌더링
- `ArtRenderer.drawTacticalIndicator(ctx, type, x, y, options)`: 도트 사슬 자물쇠(`BLOCKED_MYEOK`), 도트 관측 브래킷(`CANNON_BRIDGE`), 도트 점선 레이저(`THREAT_LINE`) 렌더링
