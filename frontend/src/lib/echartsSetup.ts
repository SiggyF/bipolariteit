// Eenmalige registratie van het Vloei-thema (zie vloeiChart.ts). Modules
// worden door de bundler gecached, dus importeren dit bestand meerdere keren
// registreert het thema maar één keer.
import * as echarts from "echarts/core";
import { registreerVloei } from "./vloeiChart";

registreerVloei(echarts);
